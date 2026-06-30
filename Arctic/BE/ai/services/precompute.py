import random
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import close_old_connections, transaction
from django.db.models import Avg, Count
from django.utils import timezone

from books.models import Book, BookStat, Collection, Review, Wishlist

from ..models import (
    DailyBookRecommendation,
    RecommendationCache,
    RecommendationState,
    UserPreference,
)
from .recommendation import (
    GLOBAL_MODEL_PATH,
    MODEL_VERSION,
    _genre_map,
    _interaction_data,
    _rank,
    _user_context,
    load_global_models,
    train_and_save_global_models,
)

CACHE_SIZE = 50
FEED_SIZE = 12
DAILY_POOL_SIZE = 20

_executor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix='recommendation-refresh',
)
_pending_user_ids = set()
_pending_lock = threading.Lock()


def rebuild_book_stats(book_ids=None):
    books = Book.objects.all()
    if book_ids is not None:
        book_ids = set(book_ids)
        books = books.filter(id__in=book_ids)
    else:
        book_ids = set(books.values_list('id', flat=True))

    review_stats = {
        row['book_id']: row
        for row in Review.objects.filter(
            book_id__in=book_ids,
        ).values('book_id').annotate(
            average_rating=Avg('rating'),
            review_count=Count('id'),
        )
    }
    wishlist_counts = {
        row['book_id']: row['count']
        for row in Wishlist.objects.filter(
            book_id__in=book_ids,
        ).values('book_id').annotate(count=Count('id'))
    }
    collection_counts = {
        row['book_id']: row['count']
        for row in Collection.objects.filter(
            book_id__in=book_ids,
        ).values('book_id').annotate(count=Count('id'))
    }

    existing = {
        stat.book_id: stat
        for stat in BookStat.objects.filter(book_id__in=book_ids)
    }
    to_create = []
    to_update = []
    books_to_update = []
    updated_at = timezone.now()

    for book in books.only('id', 'average_rating'):
        review_data = review_stats.get(book.id, {})
        average_rating = float(review_data.get('average_rating') or 0)
        values = {
            'average_rating': average_rating,
            'review_count': review_data.get('review_count', 0),
            'wishlist_count': wishlist_counts.get(book.id, 0),
            'collection_count': collection_counts.get(book.id, 0),
        }
        stat = existing.get(book.id)
        if stat is None:
            to_create.append(
                BookStat(
                    book_id=book.id,
                    updated_at=updated_at,
                    **values,
                ),
            )
        else:
            for field, value in values.items():
                setattr(stat, field, value)
            stat.updated_at = updated_at
            to_update.append(stat)

        if float(book.average_rating or 0) != average_rating:
            book.average_rating = average_rating
            books_to_update.append(book)

    if to_create:
        BookStat.objects.bulk_create(to_create)
    if to_update:
        BookStat.objects.bulk_update(
            to_update,
            [
                'average_rating',
                'review_count',
                'wishlist_count',
                'collection_count',
                'updated_at',
            ],
        )
    if books_to_update:
        Book.objects.bulk_update(books_to_update, ['average_rating'])


def rebuild_user_preference(
    user,
    genres_by_book=None,
    interaction_data=None,
):
    genres_by_book = genres_by_book or _genre_map()
    interaction_data = interaction_data or _interaction_data({user.id})
    context = _user_context(
        user,
        genres_by_book,
        interaction_data,
        stored_preference=None,
    )
    preference, _ = UserPreference.objects.update_or_create(
        user=user,
        defaults={
            'average_rating': context['user_avg_rating'],
            'genre_weights': dict(context['seed_genres']),
            'liked_genres': dict(context['liked_genres']),
            'disliked_genres': dict(context['disliked_genres']),
            'genre_average_ratings': context['genre_avg_ratings'],
            'genre_rating_counts': dict(context['genre_rating_count']),
            'author_weights': dict(context['author_weights']),
            'author_average_ratings': context['author_avg_ratings'],
            'author_rating_counts': dict(context['author_rating_count']),
        },
    )
    return preference


def rebuild_user_recommendation_cache(
    user,
    *,
    global_models=None,
    genres_by_book=None,
    interaction_data=None,
    rebuild_preference=True,
    state_marker=None,
):
    genres_by_book = genres_by_book or _genre_map()
    interaction_data = interaction_data or _interaction_data({user.id})
    if rebuild_preference:
        preference = rebuild_user_preference(
            user,
            genres_by_book,
            interaction_data,
        )
    else:
        preference = UserPreference.objects.filter(user=user).first()
        if preference is None:
            preference = rebuild_user_preference(
                user,
                genres_by_book,
                interaction_data,
            )

    global_models = global_models or load_global_models() or {}
    ranked = _rank(
        user,
        global_models=global_models,
        stored_preference=preference,
        genres_by_book=genres_by_book,
        interaction_data=interaction_data,
    )
    cache_rows = [
        RecommendationCache(
            user=user,
            book=book,
            rank=index,
            score=scores['final_score'],
            scores=scores,
            reasons=reasons,
            model_version=global_models.get('version', MODEL_VERSION),
            updated_at=timezone.now(),
        )
        for index, (book, scores, reasons) in enumerate(
            ranked[:CACHE_SIZE],
            start=1,
        )
    ]

    built_at = timezone.now()
    with transaction.atomic():
        RecommendationCache.objects.filter(user=user).delete()
        if cache_rows:
            RecommendationCache.objects.bulk_create(cache_rows)
        if state_marker is None:
            RecommendationState.objects.update_or_create(
                user=user,
                defaults={
                    'is_dirty': False,
                    'dirty_reason': '',
                    'last_built_at': built_at,
                },
            )
        else:
            # 갱신 도중 새 이벤트가 들어왔다면 그 이벤트의 dirty 상태를
            # 지우지 않는다. 작업 종료 후 한 번 더 갱신하도록 남겨 둔다.
            RecommendationState.objects.filter(
                user=user,
                is_dirty=True,
                updated_at=state_marker,
            ).update(
                is_dirty=False,
                dirty_reason='',
                last_built_at=built_at,
                updated_at=built_at,
            )
    return len(cache_rows)


def rebuild_all_recommendations(*, retrain_models=True):
    rebuild_book_stats()
    global_models = (
        train_and_save_global_models()
        if retrain_models
        else load_global_models()
    )
    if global_models is None:
        global_models = train_and_save_global_models()

    genres_by_book = _genre_map()
    interaction_data = _interaction_data()
    users = list(get_user_model().objects.filter(is_active=True))

    for user in users:
        rebuild_user_recommendation_cache(
            user,
            global_models=global_models,
            genres_by_book=genres_by_book,
            interaction_data=interaction_data,
            rebuild_preference=True,
        )
    return {
        'users': len(users),
        'books': Book.objects.count(),
        'cache_rows': RecommendationCache.objects.count(),
        'model_path': str(GLOBAL_MODEL_PATH),
    }


def bootstrap_is_complete():
    user_count = get_user_model().objects.filter(is_active=True).count()
    book_count = Book.objects.count()
    if load_global_models() is None:
        return False
    if BookStat.objects.count() != book_count:
        return False
    if UserPreference.objects.filter(user__is_active=True).count() != user_count:
        return False
    completed_users = RecommendationState.objects.filter(
        user__is_active=True,
        is_dirty=False,
        last_built_at__isnull=False,
    ).count()
    return completed_users == user_count


def ensure_recommendation_bootstrap():
    model_exists = load_global_models() is not None
    if bootstrap_is_complete():
        return None
    return rebuild_all_recommendations(retrain_models=not model_exists)


def invalidate_all_recommendations():
    RecommendationCache.objects.all().delete()
    RecommendationState.objects.all().update(
        is_dirty=True,
        dirty_reason='full_data_changed',
    )
    UserPreference.objects.all().delete()
    BookStat.objects.all().delete()
    cache.delete('ai:recommendation:global-models:v2')
    if GLOBAL_MODEL_PATH.exists():
        GLOBAL_MODEL_PATH.unlink()


def mark_users_dirty(user_ids, reason, *, schedule=True):
    user_ids = {int(user_id) for user_id in user_ids if user_id}
    if not user_ids:
        return
    existing_ids = set(
        RecommendationState.objects.filter(
            user_id__in=user_ids,
        ).values_list('user_id', flat=True),
    )
    dirty_at = timezone.now()
    RecommendationState.objects.filter(user_id__in=user_ids).update(
        is_dirty=True,
        dirty_reason=reason,
        updated_at=dirty_at,
    )
    RecommendationState.objects.bulk_create([
        RecommendationState(
            user_id=user_id,
            is_dirty=True,
            dirty_reason=reason,
            updated_at=dirty_at,
        )
        for user_id in user_ids - existing_ids
    ], ignore_conflicts=True)

    if schedule:
        transaction.on_commit(
            lambda: schedule_recommendation_refresh(user_ids),
        )


def schedule_recommendation_refresh(user_ids):
    user_ids = {int(user_id) for user_id in user_ids if user_id}
    with _pending_lock:
        new_ids = user_ids - _pending_user_ids
        _pending_user_ids.update(new_ids)
    for user_id in new_ids:
        _executor.submit(_refresh_user_worker, user_id)


def _refresh_user_worker(user_id):
    close_old_connections()
    refresh_succeeded = False
    try:
        user = get_user_model().objects.filter(
            id=user_id,
            is_active=True,
        ).first()
        if user is None:
            return
        state = RecommendationState.objects.filter(user=user).first()
        personal_preference_reasons = {
            'user_created',
            'profile_updated',
            'review_changed',
            'wishlist_changed',
            'collection_changed',
            'preferred_genre_changed',
            'full_data_changed',
        }
        rebuild_user_recommendation_cache(
            user,
            rebuild_preference=(
                state is None
                or state.dirty_reason in personal_preference_reasons
            ),
            state_marker=state.updated_at if state else None,
        )
        refresh_succeeded = True
    except Exception as error:
        print(
            f'[recommendation] 사용자 {user_id} 추천 갱신 실패: {error}',
        )
    finally:
        with _pending_lock:
            _pending_user_ids.discard(user_id)
        if (
            refresh_succeeded
            and RecommendationState.objects.filter(
                user_id=user_id,
                is_dirty=True,
            ).exists()
        ):
            schedule_recommendation_refresh([user_id])
        close_old_connections()


def cached_recommendations(user, limit=CACHE_SIZE):
    return list(
        RecommendationCache.objects.filter(user=user)
        .select_related('book', 'book__stat')
        .prefetch_related('book__genres')
        .order_by('rank')[:limit],
    )


def _pick_daily(cache_entries, today, user_id, exclude_id=None):
    # 상위 N권 중에서 날짜+유저를 시드로 점수 가중 추첨한다.
    # 같은 날에는 항상 같은 책, 다음 날에는 시드가 바뀌어 다른 책이 뽑힌다.
    pool = [
        entry
        for entry in cache_entries[:DAILY_POOL_SIZE]
        if entry.book_id != exclude_id
    ]
    if not pool:
        pool = cache_entries[:DAILY_POOL_SIZE] or list(cache_entries)
    rng = random.Random(f'{user_id}:{today.isoformat()}')
    weights = [max(float(entry.score), 0.01) for entry in pool]
    return rng.choices(pool, weights=weights, k=1)[0]


def get_or_create_daily_from_cache(user, cache_entries):
    from .recommendation import KST

    now = timezone.now().astimezone(KST)
    today = now.date()
    stored = DailyBookRecommendation.objects.select_related(
        'book',
        'book__stat',
    ).prefetch_related('book__genres').filter(
        user=user,
        recommendation_date=today,
    ).first()
    if stored:
        return stored, now
    if not cache_entries:
        return None, now

    yesterday_id = DailyBookRecommendation.objects.filter(
        user=user,
        recommendation_date=today - timedelta(days=1),
    ).values_list('book_id', flat=True).first()
    selected = _pick_daily(cache_entries, today, user.id, exclude_id=yesterday_id)
    daily, _ = DailyBookRecommendation.objects.update_or_create(
        user=user,
        recommendation_date=today,
        defaults={
            'book': selected.book,
            'scores': selected.scores,
            'candidate_sources': selected.reasons,
        },
    )
    daily.book = selected.book
    return daily, now


def cached_feed(cache_entries, excluded_book_id=None, limit=FEED_SIZE):
    pool = [
        entry
        for entry in cache_entries
        if entry.book_id != excluded_book_id
    ]
    if not pool:
        return []
    return random.SystemRandom().sample(pool, min(limit, len(pool)))
