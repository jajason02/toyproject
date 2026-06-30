import hashlib
import math
import pickle
import random
from collections import defaultdict
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count

from accounts.models import Follow, UserGenre
from books.models import Book, BookGenre, BookStat, Collection, Review, Wishlist

from ..models import DailyBookRecommendation, UserPreference

KST = ZoneInfo('Asia/Seoul')
MODEL_CACHE_TIMEOUT = 60 * 60
MODEL_VERSION = 'recommendation-v2'
MODEL_DIRECTORY = Path(
    getattr(
        settings,
        'RECOMMENDATION_MODEL_DIR',
        settings.BASE_DIR / 'recommendation_models',
    ),
)
GLOBAL_MODEL_PATH = MODEL_DIRECTORY / 'global_models.pkl'


def _model_signature(*values):
    payload = pickle.dumps(values, protocol=pickle.HIGHEST_PROTOCOL)
    return hashlib.blake2b(payload, digest_size=16).hexdigest()


def _genre_map():
    genres_by_book = defaultdict(set)
    for book_id, genre_id in BookGenre.objects.values_list(
        'book_id',
        'genre_id',
    ):
        genres_by_book[book_id].add(genre_id)
    return genres_by_book


def _interaction_data(user_ids=None):
    target_user_ids = (
        {int(user_id) for user_id in user_ids}
        if user_ids is not None
        else None
    )
    preferred_by_user = defaultdict(set)
    wishlist_by_user = defaultdict(set)
    collection_by_user = defaultdict(set)
    reviews_by_user = defaultdict(list)
    following_by_user = defaultdict(set)

    preferred_rows = UserGenre.objects.all()
    following_rows = Follow.objects.all()
    if target_user_ids is not None:
        preferred_rows = preferred_rows.filter(user_id__in=target_user_ids)
        following_rows = following_rows.filter(
            from_user_id__in=target_user_ids,
        )

    for user_id, genre_id in preferred_rows.values_list(
        'user_id',
        'genre_id',
    ):
        preferred_by_user[user_id].add(genre_id)

    for from_user_id, to_user_id in following_rows.values_list(
        'from_user_id',
        'to_user_id',
    ):
        following_by_user[from_user_id].add(to_user_id)

    behavior_user_ids = None
    if target_user_ids is not None:
        followed_user_ids = {
            followed_user_id
            for user_ids_set in following_by_user.values()
            for followed_user_id in user_ids_set
        }
        behavior_user_ids = target_user_ids | followed_user_ids

    wishlist_rows = Wishlist.objects.all()
    collection_rows = Collection.objects.all()
    review_rows = Review.objects.all()
    if behavior_user_ids is not None:
        wishlist_rows = wishlist_rows.filter(user_id__in=behavior_user_ids)
        collection_rows = collection_rows.filter(
            user_id__in=behavior_user_ids,
        )
        review_rows = review_rows.filter(user_id__in=behavior_user_ids)

    for user_id, book_id in wishlist_rows.values_list(
        'user_id',
        'book_id',
    ):
        wishlist_by_user[user_id].add(book_id)

    for user_id, book_id in collection_rows.values_list(
        'user_id',
        'book_id',
    ):
        collection_by_user[user_id].add(book_id)

    for user_id, book_id, rating, author in review_rows.values_list(
        'user_id',
        'book_id',
        'rating',
        'book__author',
    ):
        reviews_by_user[user_id].append((book_id, rating, author))

    review_counts = dict(
        BookStat.objects.values_list('book_id', 'review_count'),
    )
    if not review_counts:
        review_counts = {
            row['book_id']: row['count']
            for row in Review.objects.values('book_id').annotate(
                count=Count('id'),
            )
        }

    return {
        'preferred_by_user': preferred_by_user,
        'wishlist_by_user': wishlist_by_user,
        'collection_by_user': collection_by_user,
        'reviews_by_user': reviews_by_user,
        'following_by_user': following_by_user,
        'review_counts': review_counts,
    }


def _number_map(values, key_type=str):
    return defaultdict(
        float,
        {
            key_type(key): float(value)
            for key, value in (values or {}).items()
        },
    )


def _count_map(values, key_type=str):
    return defaultdict(
        int,
        {
            key_type(key): int(value)
            for key, value in (values or {}).items()
        },
    )


def _user_context(
    user,
    genres_by_book,
    interaction_data=None,
    stored_preference=None,
):
    data = interaction_data or _interaction_data()
    user_id = user.id
    preferred = set(data['preferred_by_user'].get(user_id, set()))

    if stored_preference is not None:
        liked_genres = _number_map(stored_preference.liked_genres, int)
        disliked_genres = _number_map(
            stored_preference.disliked_genres,
            int,
        )
        seed_genres = _number_map(stored_preference.genre_weights, int)
        author_weights = _number_map(stored_preference.author_weights)
        genre_avg_ratings = {
            int(key): float(value)
            for key, value in stored_preference.genre_average_ratings.items()
        }
        genre_rating_count = _count_map(
            stored_preference.genre_rating_counts,
            int,
        )
        author_avg_ratings = {
            key: float(value)
            for key, value in stored_preference.author_average_ratings.items()
        }
        author_rating_count = _count_map(
            stored_preference.author_rating_counts,
        )
        user_avg_rating = float(stored_preference.average_rating)
    else:
        liked_genres = defaultdict(float)
        disliked_genres = defaultdict(float)
        seed_genres = defaultdict(float)
        author_weights = defaultdict(float)
        genre_rating_sum = defaultdict(float)
        genre_rating_count = defaultdict(int)
        author_rating_sum = defaultdict(float)
        author_rating_count = defaultdict(int)
        user_rating_sum = 0.0
        user_rating_count = 0

        for book_id in data['wishlist_by_user'].get(user_id, set()):
            for genre_id in genres_by_book.get(book_id, set()):
                seed_genres[genre_id] += 0.33

        for book_id in data['collection_by_user'].get(user_id, set()):
            for genre_id in genres_by_book.get(book_id, set()):
                seed_genres[genre_id] += 0.4

        user_reviews = data['reviews_by_user'].get(user_id, [])
        for book_id, rating, author in user_reviews:
            rating = float(rating)
            genre_weight = rating_to_genre_weight(rating)
            author_weight = rating_to_author_weight(rating)
            user_rating_sum += rating
            user_rating_count += 1

            for genre_id in genres_by_book.get(book_id, set()):
                seed_genres[genre_id] += genre_weight
                genre_rating_sum[genre_id] += rating
                genre_rating_count[genre_id] += 1
                if rating >= 4:
                    liked_genres[genre_id] += rating - 3
                elif rating <= 2:
                    disliked_genres[genre_id] += 3 - rating

            if author:
                author_weights[author] += author_weight
                author_rating_sum[author] += rating
                author_rating_count[author] += 1

        user_avg_rating = (
            user_rating_sum / user_rating_count
            if user_rating_count else 3.0
        )
        genre_avg_ratings = {
            genre_id: genre_rating_sum[genre_id] / genre_rating_count[genre_id]
            for genre_id in genre_rating_sum
        }
        author_avg_ratings = {
            author: author_rating_sum[author] / author_rating_count[author]
            for author in author_rating_sum
        }

    following_ids = data['following_by_user'].get(user_id, set())

    reviews = defaultdict(list)
    wishlists = defaultdict(int)
    collections = defaultdict(int)

    for following_id in following_ids:
        for book_id, rating, _ in data['reviews_by_user'].get(
            following_id,
            [],
        ):
            reviews[book_id].append(rating)

        for book_id in data['wishlist_by_user'].get(following_id, set()):
            wishlists[book_id] += 1

        for book_id in data['collection_by_user'].get(following_id, set()):
            collections[book_id] += 1

    return {
        'preferred': preferred,
        'seed_genres': seed_genres,
        'author_weights': author_weights,

        'liked_genres': liked_genres,
        'disliked_genres': disliked_genres,

        'user_avg_rating': user_avg_rating,
        'genre_avg_ratings': genre_avg_ratings,
        'genre_rating_count': genre_rating_count,
        'author_avg_ratings': author_avg_ratings,
        'author_rating_count': author_rating_count,

        'following_count': max(len(following_ids), 1),
        'reviews': reviews,
        'wishlists': wishlists,
        'collections': collections,
        'review_counts': data['review_counts'],
    }

def rating_to_genre_weight(rating):
    if rating >= 5:
        return 0.6
    if rating >= 4:
        return 0.35
    if rating >= 3:
        return 0.1
    return 0.0


def rating_to_author_weight(rating):
    if rating >= 5:
        return 1.0
    if rating >= 4:
        return 0.6
    if rating >= 3:
        return 0.0
    if rating >= 2:
        return -0.5
    return -1.0


def _features(book, genres_by_book, context):
    genres = genres_by_book.get(book.id, set())
    social_ratings = context['reviews'].get(book.id, [])

    # 1. 선호 장르 일치 점수
    preferred_score = (
        len(genres & context['preferred']) / max(len(genres), 1)
    )

    # 2. 내 행동 기반 장르 점수
    seed_genres = context.get('seed_genres', {})

    seed_genre_weights = {
        genre_id: max(weight, 0)
        for genre_id, weight in seed_genres.items()
    }

    genre_weight_total = sum(seed_genree_weight for seed_genree_weight in seed_genre_weights.values()) or 1

    item_genre_score = sum(
        seed_genre_weights.get(genre_id, 0)
        for genre_id in genres
    ) / genre_weight_total

    item_genre_score = max(min(item_genre_score, 1), 0)

    # 3. 팔로잉 유저 리뷰 평점 점수
    following_review_score = (
        sum(social_ratings) / (len(social_ratings) * 5)
        if social_ratings else 0
    )

    # 4. 팔로잉 유저 위시리스트 반응 점수
    following_wishlist_score = min(
        context['wishlists'].get(book.id, 0) / context['following_count'],
        1,
    )

    # 5. 팔로잉 유저 컬렉션 반응 점수
    following_collection_score = min(
        context['collections'].get(book.id, 0) / context['following_count'],
        1,
    )

    # 6. 책 자체 평균 평점 점수 (리뷰 수 기반 베이지안 축소)
    # 리뷰가 적은 책(예: 리뷰 2개에 5점)이 만점으로 과대평가되어 추천을
    # 독식하지 않도록, 리뷰 수가 적을수록 전역 평균(3.0)으로 끌어내린다.
    stat = getattr(book, 'stat', None)
    average_rating = (
        stat.average_rating
        if stat is not None
        else book.average_rating
    )
    review_count = (
        stat.review_count
        if stat is not None
        else context['review_counts'].get(book.id, 0)
    )
    shrink_constant = 10
    global_mean_rating = 3.0
    shrunk_rating = (
        review_count * float(average_rating or 0)
        + shrink_constant * global_mean_rating
    ) / (review_count + shrink_constant)
    book_rating_score = min(shrunk_rating / 5, 1)

    # 7. 리뷰 수 점수
    review_count_score = min(
        math.log1p(context['review_counts'].get(book.id, 0)) / math.log(21),
        1,
    )

    # 8. 작가 선호 점수
    # 5점 준 작가면 플러스, 1~2점 준 작가면 마이너스
    author_weights = context.get('author_weights', {})
    author_score = author_weights.get(book.author, 0)
    author_score = max(min(author_score, 1), -1)

    # 9. 내가 이 책의 장르들에 평균 몇 점을 줬는가
    genre_avg_ratings = context.get('genre_avg_ratings', {})
    genre_rating_count = context.get('genre_rating_count', {})
    user_avg_rating = context.get('user_avg_rating', 3.0)

    matched_genre_rating_sum = 0.0
    matched_genre_count_sum = 0

    for genre_id in genres:
        count = genre_rating_count.get(genre_id, 0)
        if count > 0:
            matched_genre_rating_sum += genre_avg_ratings[genre_id] * count
            matched_genre_count_sum += count

    reviewed_genre_avg_rating = (
        matched_genre_rating_sum / matched_genre_count_sum
        if matched_genre_count_sum else user_avg_rating
    )

    reviewed_genre_rating_score = min(
        max(reviewed_genre_avg_rating / 5, 0),
        1,
    )

    # 내가 이 장르를 얼마나 많이 평가했는지
    reviewed_genre_confidence = min(
        math.log1p(matched_genre_count_sum) / math.log(11),
        1,
    )

    # 10. 내가 이 작가에게 평균 몇 점을 줬는가
    author_avg_ratings = context.get('author_avg_ratings', {})
    author_rating_count = context.get('author_rating_count', {})

    author_count = author_rating_count.get(book.author, 0)

    reviewed_author_avg_rating = (
        author_avg_ratings.get(book.author, user_avg_rating)
        if book.author else user_avg_rating
    )

    reviewed_author_rating_score = min(
        max(reviewed_author_avg_rating / 5, 0),
        1,
    )

    # 내가 이 작가를 얼마나 많이 평가했는지
    reviewed_author_confidence = min(
        math.log1p(author_count) / math.log(6),
        1,
    )

    liked_genres = context.get('liked_genres', {})
    disliked_genres = context.get('disliked_genres', {})

    liked_total = sum(liked_genres.values()) or 1
    disliked_total = sum(disliked_genres.values()) or 1

    liked_genre_score = sum(
        liked_genres.get(genre_id, 0)
        for genre_id in genres
    ) / liked_total

    disliked_genre_score = sum(
        disliked_genres.get(genre_id, 0)
        for genre_id in genres
    ) / disliked_total

    liked_genre_score = max(min(liked_genre_score, 1), 0)
    disliked_genre_score = max(min(disliked_genre_score, 1), 0)

    has_reviewed_author = 1 if author_count > 0 else 0
    has_reviewed_genre = 1 if matched_genre_count_sum > 0 else 0

    return [
        preferred_score,                # 0
        item_genre_score,               # 1
        following_review_score,         # 2
        following_wishlist_score,       # 3
        following_collection_score,     # 4
        book_rating_score,              # 5
        review_count_score,             # 6
        author_score,                   # 7

        reviewed_genre_rating_score,    # 8
        reviewed_genre_confidence,      # 9
        reviewed_author_rating_score,   # 10
        reviewed_author_confidence,     # 11

        liked_genre_score,              # 12
        disliked_genre_score,           # 13
        has_reviewed_genre,             # 14
        has_reviewed_author,            # 15
    ]


def _candidates(
    user,
    genres_by_book,
    context,
    interaction_data=None,
):
    data = interaction_data or _interaction_data()
    user_id = user.id
    interacted = {
        book_id
        for book_id, _, _ in data['reviews_by_user'].get(user_id, [])
    }
    interacted.update(data['wishlist_by_user'].get(user_id, set()))
    interacted.update(data['collection_by_user'].get(user_id, set()))

    sources = defaultdict(set)

    positive_seed_genres = {
        genre_id
        for genre_id, weight in context['seed_genres'].items()
        if weight > 0
    }

    for book_id, genres in genres_by_book.items():
        if genres & context['preferred']:
            sources[book_id].add('preferred_genre')

        if genres & positive_seed_genres:
            sources[book_id].add('similar_item')

    for book_id in context['reviews']:
        sources[book_id].add('following_review')

    for book_id in context['wishlists']:
        sources[book_id].add('following_wishlist')

    for book_id in context['collections']:
        sources[book_id].add('following_collection')

    popular_ids = BookStat.objects.order_by(
        '-wishlist_count',
        '-collection_count',
        '-review_count',
    ).values_list('book_id', flat=True)[:40]
    for book_id in popular_ids:
        sources[book_id].add('popular')

    recent_ids = Book.objects.order_by(
        '-published_date',
        '-id',
    ).values_list('id', flat=True)[:10]
    for book_id in recent_ids:
        sources[book_id].add('new_release')

    ids = set(sources) - interacted

    books = list(
        Book.objects.filter(id__in=ids)
        .select_related('stat')
        .prefetch_related('genres')
        .order_by('-stat__review_count', '-published_date')[:300]
    )

    if not books:
        books = list(
            Book.objects.exclude(id__in=interacted)
            .select_related('stat')
            .prefetch_related('genres')
            .order_by(
                '-stat__wishlist_count',
                '-stat__collection_count',
                '-published_date',
            )[:100]
        )
        for book in books:
            sources[book.id].add('popular_fallback')

    return books, sources

def _training_data(genres_by_book, interaction_data=None, books=None):
    data = interaction_data or _interaction_data()
    users = list(get_user_model().objects.all())
    books = books or list(Book.objects.all())
    wishlist_pairs = {
        (user_id, book_id)
        for user_id, book_ids in data['wishlist_by_user'].items()
        for book_id in book_ids
    }
    collection_pairs = {
        (user_id, book_id)
        for user_id, book_ids in data['collection_by_user'].items()
        for book_id in book_ids
    }
    ratings = {
        (user_id, book_id): rating
        for user_id, reviews in data['reviews_by_user'].items()
        for book_id, rating, _ in reviews
    }
    interactions_by_user = defaultdict(set)
    for user_id, book_id in wishlist_pairs | collection_pairs | set(ratings):
        interactions_by_user[user_id].add(book_id)

    rows, wishlist_y, collection_y, positive_y, rating_rows = [], [], [], [], []

    for user in users:
        context = _user_context(user, genres_by_book, data)
        positive_ids = interactions_by_user.get(user.id, set())
        negatives = [book for book in books if book.id not in positive_ids]
        random.Random(user.id).shuffle(negatives)
        selected = positive_ids | {
            book.id for book in negatives[:max(20, len(positive_ids) * 2)]
        }
        for book in books:
            if book.id not in selected:
                continue
            pair = (user.id, book.id)
            row = _features(book, genres_by_book, context)
            rows.append(row)
            wishlist_y.append(int(pair in wishlist_pairs))
            collection_y.append(int(pair in collection_pairs))
            positive_y.append(int(ratings.get(pair, 0) >= 4))
            if pair in ratings:
                rating_rows.append((row, ratings[pair]))
    return rows, wishlist_y, collection_y, positive_y, rating_rows


def _classification(
    rows,
    labels,
    candidates,
    fallback_index,
    model_cache_key=None,
    trained_model=None,
):
    if trained_model is not None:
        model, class_index = trained_model
        return [
            float(probability[class_index])
            for probability in model.predict_proba(candidates)
        ]

    if len(rows) >= 10 and len(set(labels)) == 2:
        try:
            from sklearn.ensemble import RandomForestClassifier

            cached_model = (
                cache.get(model_cache_key)
                if model_cache_key else None
            )
            if cached_model is None:
                model = RandomForestClassifier(
                    n_estimators=160,
                    max_depth=8,
                    min_samples_leaf=2,
                    class_weight='balanced',
                    random_state=42,
                    n_jobs=-1,
                )
                model.fit(rows, labels)
                class_index = list(model.classes_).index(1)
                if model_cache_key:
                    cache.set(
                        model_cache_key,
                        (model, class_index),
                        timeout=MODEL_CACHE_TIMEOUT,
                    )
            else:
                model, class_index = cached_model

            return [
                float(probability[class_index])
                for probability in model.predict_proba(candidates)
            ]
        except ImportError:
            pass
    return [min(max(row[fallback_index], 0), 1) for row in candidates]


def _fit_classifier(rows, labels):
    if len(rows) < 10 or len(set(labels)) != 2:
        return None

    from sklearn.ensemble import RandomForestClassifier

    model = RandomForestClassifier(
        n_estimators=160,
        max_depth=8,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
    )
    model.fit(rows, labels)
    class_index = list(model.classes_).index(1)
    return model, class_index


def train_and_save_global_models():
    genres_by_book = _genre_map()
    interaction_data = _interaction_data()
    books = list(Book.objects.select_related('stat').all())
    rows, wishlist_y, collection_y, positive_y, _ = _training_data(
        genres_by_book,
        interaction_data,
        books,
    )
    payload = {
        'version': MODEL_VERSION,
        'wishlist': _fit_classifier(rows, wishlist_y),
        'collection': _fit_classifier(rows, collection_y),
        'positive': _fit_classifier(rows, positive_y),
    }
    MODEL_DIRECTORY.mkdir(parents=True, exist_ok=True)
    temporary_path = GLOBAL_MODEL_PATH.with_suffix('.tmp')
    with temporary_path.open('wb') as model_file:
        pickle.dump(payload, model_file, protocol=pickle.HIGHEST_PROTOCOL)
    temporary_path.replace(GLOBAL_MODEL_PATH)
    cache.set(
        'ai:recommendation:global-models:v2',
        payload,
        timeout=None,
    )
    return payload


def load_global_models():
    cache_key = 'ai:recommendation:global-models:v2'
    payload = cache.get(cache_key)
    if payload is not None:
        return payload
    if not GLOBAL_MODEL_PATH.exists():
        return None
    try:
        with GLOBAL_MODEL_PATH.open('rb') as model_file:
            payload = pickle.load(model_file)
    except (
        OSError,
        pickle.PickleError,
        EOFError,
        AttributeError,
        ValueError,
        ImportError,
    ):
        return None
    if payload.get('version') != MODEL_VERSION:
        return None
    cache.set(cache_key, payload, timeout=None)
    return payload


def _recommendation_rating(row, user_avg_rating):
    preferred_score = row[0]
    item_genre_score = row[1]
    following_review_score = row[2]
    book_rating_score = row[5]
    author_score = row[7]

    reviewed_genre_rating = row[8] * 5
    reviewed_genre_confidence = row[9]
    reviewed_author_rating = row[10] * 5
    reviewed_author_confidence = row[11]

    liked_genre_score = row[12]
    disliked_genre_score = row[13]

    # 추천 후보라는 긍정 신호와 사용자의 평점 성향을 함께 반영한다.
    predicted = 3.4 + (user_avg_rating - 3.0) * 0.35
    predicted = min(max(predicted, 3.2), 4.1)

    predicted += 0.35 * preferred_score
    predicted += 0.35 * item_genre_score
    predicted += 0.45 * liked_genre_score
    predicted -= 0.30 * disliked_genre_score

    predicted += (
        (reviewed_genre_rating - user_avg_rating)
        * reviewed_genre_confidence
        * 0.35
    )
    predicted += (
        (reviewed_author_rating - user_avg_rating)
        * reviewed_author_confidence
        * 0.45
    )

    predicted += 0.20 * author_score

    if following_review_score > 0:
        predicted += (following_review_score - 0.6) * 0.30

    if book_rating_score > 0:
        predicted += (book_rating_score * 5 - 3.5) * 0.08

    return min(max(predicted, 3.0), 5.0)


def _regression(rating_rows, candidates, model_cache_key=None):
    user_avg_rating = (
        sum(rating for _, rating in rating_rows) / len(rating_rows)
        if rating_rows else 3.0
    )

    unique_ratings = set(rating for _, rating in rating_rows)
    recommendation_predictions = [
        _recommendation_rating(row, user_avg_rating)
        for row in candidates
    ]

    # 내 리뷰가 5개 이상이고, 평점 종류가 2개 이상이면 랜덤포레스트 학습
    if len(rating_rows) >= 5 and len(unique_ratings) >= 2:
        try:
            from sklearn.ensemble import RandomForestRegressor

            model = (
                cache.get(model_cache_key)
                if model_cache_key else None
            )
            if model is None:
                model = RandomForestRegressor(
                    n_estimators=200,
                    max_depth=7,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                )

                model.fit(
                    [row for row, _ in rating_rows],
                    [rating for _, rating in rating_rows],
                )
                if model_cache_key:
                    cache.set(
                        model_cache_key,
                        model,
                        timeout=MODEL_CACHE_TIMEOUT,
                    )

            raw_predictions = model.predict(candidates)

            adjusted_predictions = []

            for raw_value, recommendation_value in zip(
                raw_predictions,
                recommendation_predictions,
            ):
                # 모델은 사용자의 절대 평점대가 아니라 평균 대비 선호도
                # 보정값으로 사용한다. 낮은 평점을 자주 주는 사용자도
                # 추천 후보 전체가 1~2점대로 눌리지 않게 하기 위함이다.
                model_adjustment = (
                    float(raw_value) - user_avg_rating
                ) * 0.30
                adjusted = recommendation_value + model_adjustment
                adjusted = min(max(adjusted, 3.0), 5.0)

                adjusted_predictions.append(round(adjusted, 3))

            return adjusted_predictions

        except ImportError:
            pass

    return [round(value, 3) for value in recommendation_predictions]



def _rank(
    user,
    global_models=None,
    stored_preference=None,
    genres_by_book=None,
    interaction_data=None,
):
    genres_by_book = genres_by_book or _genre_map()
    interaction_data = interaction_data or _interaction_data()
    if stored_preference is None:
        stored_preference = UserPreference.objects.filter(user=user).first()
    context = _user_context(
        user,
        genres_by_book,
        interaction_data,
        stored_preference,
    )
    books, sources = _candidates(
        user,
        genres_by_book,
        context,
        interaction_data,
    )
    if not books:
        return []

    candidates = [_features(book, genres_by_book, context) for book in books]
    global_models = global_models or load_global_models() or {}

    wishlist_p = _classification(
        [],
        [],
        candidates,
        0,
        trained_model=global_models.get('wishlist'),
    )
    collection_p = _classification(
        [],
        [],
        candidates,
        1,
        trained_model=global_models.get('collection'),
    )
    positive_p = _classification(
        [],
        [],
        candidates,
        5,
        trained_model=global_models.get('positive'),
    )

    user_rating_rows = _user_rating_rows(
        user,
        genres_by_book,
        context,
        interaction_data,
    )
    rating_signature = _model_signature(user_rating_rows)
    ratings = _regression(
        user_rating_rows,
        candidates,
        (
            f'ai:recommendation:rating:v1:{user.id}:'
            f'{rating_signature}'
        ),
    )

    ranked = []
    for index, book in enumerate(books):
        following_score = (
            candidates[index][2] * 0.5
            + candidates[index][3] * 0.2
            + candidates[index][4] * 0.3
        )
        scores = {
            'wishlist_probability': round(wishlist_p[index], 4),
            'collection_probability': round(collection_p[index], 4),
            'positive_probability': round(positive_p[index], 4),
            'expected_rating': round(ratings[index], 3),
            'following_reaction_score': round(following_score, 4),
            'author_score': round(candidates[index][7], 4),
        }

        rating_score = ratings[index] / 5
        author_score = candidates[index][7]

        final_score = (
            0.20 * wishlist_p[index]
            + 0.15 * collection_p[index]
            + 0.25 * positive_p[index]
            + 0.20 * rating_score
            + 0.10 * following_score
            + 0.10 * author_score
        )

        scores['final_score'] = round(final_score, 4)
        ranked.append((book, scores, sorted(sources[book.id])))
    return sorted(ranked, key=lambda item: item[1]['final_score'], reverse=True)


def get_daily_recommendation(user):
    now = datetime.now(KST)
    today = now.date()
    stored = DailyBookRecommendation.objects.select_related('book').filter(
        user=user,
        recommendation_date=today,
    ).first()
    if stored:
        return stored, now, None

    ranked = _rank(user)
    if not ranked:
        return None, now, ranked

    yesterday_id = DailyBookRecommendation.objects.filter(
        user=user,
        recommendation_date=today - timedelta(days=1),
    ).values_list('book_id', flat=True).first()
    book, scores, sources = next(
        (item for item in ranked if item[0].id != yesterday_id),
        ranked[0],
    )
    with transaction.atomic():
        recommendation, _ = DailyBookRecommendation.objects.update_or_create(
            user=user,
            recommendation_date=today,
            defaults={
                'book': book,
                'scores': scores,
                'candidate_sources': sources,
            },
        )
    return recommendation, now, ranked

def _user_rating_rows(
    user,
    genres_by_book,
    context,
    interaction_data=None,
    books_by_id=None,
):
    rating_rows = []
    data = interaction_data or _interaction_data()
    reviews = data['reviews_by_user'].get(user.id, [])

    if books_by_id is None:
        review_book_ids = [book_id for book_id, _, _ in reviews]
        books_by_id = {
            book.id: book
            for book in Book.objects.filter(id__in=review_book_ids)
        }

    for book_id, rating, _ in reviews:
        book = books_by_id.get(book_id)
        if book is None:
            continue
        row = _features(book, genres_by_book, context)
        rating_rows.append((row, rating))

    return rating_rows


def get_feed_recommendations(
    user,
    excluded_book_id=None,
    limit=12,
    ranked=None,
):
    if ranked is None:
        ranked = _rank(user)
    pool = [
        item for item in ranked[:50]
        if item[0].id != excluded_book_id
    ]
    if not pool:
        return []
    return random.SystemRandom().sample(pool, min(limit, len(pool)))


def next_kst_midnight(now):
    return datetime.combine(
        now.date() + timedelta(days=1),
        time.min,
        tzinfo=KST,
    )
