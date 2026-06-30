import json
import random
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.db.models import Avg

from accounts.models import Follow, UserGenre
from books.models import (
    Book,
    BookGenre,
    Collection,
    Genre,
    Review,
    ReviewLike,
    Wishlist,
)
from community.models import (
    Comment,
    CommentLike,
    Thread,
    ThreadLike,
)


PREFERRED_GENRE_PATTERNS = [
    ['소설/시/희곡', '인문/교양', '예술/대중문화'],
    ['경제/경영', '자기계발', '인문/교양'],
    ['자기계발', '취미/실용', '경제/경영'],
    ['인문/교양', '과학', '소설/시/희곡'],
    ['어린이/청소년', '만화/라이트노벨', '소설/시/희곡'],
    ['소설/시/희곡', '예술/대중문화', '취미/실용'],
    ['외국어/외국도서', '취미/실용', '자기계발'],
    ['과학', '경제/경영', '인문/교양'],
    ['만화/라이트노벨', '소설/시/희곡', '어린이/청소년'],
    ['예술/대중문화', '인문/교양', '소설/시/희곡'],
]


THREAD_TITLE_TEMPLATES = [
    '[더미] 요즘 읽기 좋은 책 추천해 주세요 #{number}',
    '[더미] {book_title} 읽어본 사람 있나요? #{number}',
    '[더미] 책장에 넣어둘 만한 인생책 공유 #{number}',
    '[더미] 이번 주 독서 계획 같이 세워봐요 #{number}',
    '[더미] 장르별 추천 알고리즘 테스트 게시글 #{number}',
    '[더미] 완독 후 여운이 긴 책 이야기 #{number}',
]

THREAD_CONTENT_TEMPLATES = [
    '최근에 "{book_title}"을(를) 보고 관심이 생겼습니다. 비슷한 분위기의 책을 추천받고 싶어요.',
    '커뮤니티 화면 테스트용 게시글입니다. 댓글, 좋아요, 정렬, 상세 페이지 동작을 확인하기 위한 내용입니다.',
    '책 취향이 비슷한 유저들과 읽은 책 이야기를 나눠보고 싶습니다. 여러분의 최근 완독작은 무엇인가요?',
    '위시리스트에 담아둔 책이 너무 많아서 우선순위를 정하기 어렵네요. 가볍게 읽기 좋은 책을 알려주세요.',
    '추천 알고리즘이 커뮤니티 활동까지 반영되는지 확인하기 위한 더미 게시글입니다.',
]

COMMENT_CONTENT_TEMPLATES = [
    '저도 이 주제 궁금했어요. "{book_title}"도 같이 보면 좋을 것 같습니다.',
    '추천 감사합니다. 나중에 위시리스트에 담아두고 읽어볼게요.',
    '비슷한 취향이면 이 책도 잘 맞을 것 같아요.',
    '커뮤니티 댓글 렌더링 테스트용 더미 댓글입니다.',
    '좋아요 수와 댓글 정렬이 잘 보이는지 확인하기 좋은 데이터네요.',
    '저는 완독 후 리뷰까지 남겨보려고 합니다.',
    '책장 화면에서 같이 보여주면 더 자연스러울 것 같아요.',
]


class Command(BaseCommand):
    help = 'JSON fixture 기반 책/장르/유저 활동/커뮤니티 더미데이터를 생성합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='더미 유저들의 기존 리뷰/위시리스트/컬렉션/팔로우/선호장르/커뮤니티 데이터를 삭제한 뒤 다시 생성합니다.',
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=20240625,
            help='랜덤 결과를 재현하기 위한 seed 값입니다.',
        )
        parser.add_argument(
            '--latest-pool-size',
            type=int,
            default=300,
            help='published_date 최신순 상위 몇 권 안에서 리뷰/위시리스트/컬렉션 책을 랜덤 선택할지 정합니다.',
        )
        parser.add_argument(
            '--reviews-per-user',
            type=int,
            default=80,
            help='유저 1명당 생성할 리뷰 수입니다. 5개 초과가 되도록 최소 6개로 보정됩니다.',
        )
        parser.add_argument(
            '--threads-per-user',
            type=int,
            default=3,
            help='유저 1명당 생성할 커뮤니티 게시글 수입니다. 최소 1개로 보정됩니다.',
        )
        parser.add_argument(
            '--comments-per-thread',
            type=int,
            default=4,
            help='게시글 1개당 생성할 댓글 수입니다. 0개 이상으로 보정됩니다.',
        )
        parser.add_argument(
            '--thread-likes-min',
            type=int,
            default=8,
            help='게시글 1개당 최소 좋아요 수입니다.',
        )
        parser.add_argument(
            '--thread-likes-max',
            type=int,
            default=25,
            help='게시글 1개당 최대 좋아요 수입니다.',
        )
        parser.add_argument(
            '--comment-likes-min',
            type=int,
            default=1,
            help='댓글 1개당 최소 좋아요 수입니다.',
        )
        parser.add_argument(
            '--comment-likes-max',
            type=int,
            default=10,
            help='댓글 1개당 최대 좋아요 수입니다.',
        )
        parser.add_argument(
            '--books-json',
            type=str,
            default='',
            help='books.json 경로입니다. 생략하면 프로젝트 내부 후보 경로에서 자동 탐색합니다.',
        )
        parser.add_argument(
            '--genres-json',
            type=str,
            default='',
            help='categories.json 경로입니다. 생략하면 프로젝트 내부 후보 경로에서 자동 탐색합니다.',
        )
        parser.add_argument(
            '--book-genres-json',
            type=str,
            default='',
            help='book_genres.json 경로입니다. 생략하면 프로젝트 내부 후보 경로에서 자동 탐색합니다.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options['seed'])

        books_path = self.resolve_json_path(options['books_json'], 'books.json')
        genres_path = self.resolve_json_path(options['genres_json'], 'categories.json')
        book_genres_path = self.resolve_json_path(
            options['book_genres_json'],
            'book_genres.json',
        )

        genre_items = self.load_fixture(genres_path)
        book_items = self.load_fixture(books_path)
        book_genre_items = self.load_fixture(book_genres_path)

        self.validate_fixture_models(genre_items, 'books.genre', genres_path)
        self.validate_fixture_models(book_items, 'books.book', books_path)
        self.validate_fixture_models(book_genre_items, 'books.bookgenre', book_genres_path)

        users = self.create_users()

        if options['reset']:
            self.reset_dummy_user_data(users)

        genre_by_fixture_pk = self.create_genres(genre_items)
        book_by_fixture_pk = self.create_books(book_items)
        book_genre_count = self.create_book_genres(
            book_genre_items,
            book_by_fixture_pk,
            genre_by_fixture_pk,
        )

        user_genre_count = self.create_user_genres(users)
        follow_count = self.create_follows(users)

        latest_books = self.get_latest_books(options['latest_pool_size'])

        review_count = max(6, options['reviews_per_user'])
        created_reviews, updated_reviews = self.create_reviews(
            users,
            latest_books,
            review_count,
            rng,
        )

        created_wishlists, skipped_wishlists, created_collections, skipped_collections = (
            self.create_wishlists_and_collections(users, latest_books, rng)
        )

        community_counts = self.create_community_data(
            users=users,
            latest_books=latest_books,
            threads_per_user=options['threads_per_user'],
            comments_per_thread=options['comments_per_thread'],
            thread_likes_min=options['thread_likes_min'],
            thread_likes_max=options['thread_likes_max'],
            comment_likes_min=options['comment_likes_min'],
            comment_likes_max=options['comment_likes_max'],
            rng=rng,
        )

        updated_average_rating_count = self.update_book_average_ratings()
        from ai.services.precompute import invalidate_all_recommendations
        invalidate_all_recommendations()

        self.stdout.write(
            self.style.SUCCESS(
                '\n더미데이터 생성 완료\n'
                f'- 유저: {len(users)}명\n'
                f'- 장르: {len(genre_by_fixture_pk)}개\n'
                f'- 책: {len(book_by_fixture_pk)}권\n'
                f'- 책-장르 연결: {book_genre_count}개\n'
                f'- 유저 선호장르 연결: {user_genre_count}개\n'
                f'- 팔로우 관계: {follow_count}개\n'
                f'- 리뷰: 생성 {created_reviews}개, 업데이트 {updated_reviews}개\n'
                f'- 위시리스트: 생성 {created_wishlists}개, 중복/충돌 스킵 {skipped_wishlists}개\n'
                f'- 컬렉션: 생성 {created_collections}개, 중복/충돌 스킵 {skipped_collections}개\n'
                f'- 커뮤니티 게시글: 생성 {community_counts["threads"]}개\n'
                f'- 커뮤니티 댓글: 생성 {community_counts["comments"]}개\n'
                f'- 게시글 좋아요: 생성 {community_counts["thread_likes"]}개, 스킵 {community_counts["skipped_thread_likes"]}개\n'
                f'- 댓글 좋아요: 생성 {community_counts["comment_likes"]}개, 스킵 {community_counts["skipped_comment_likes"]}개\n'
                f'- 평균 평점 갱신 책 수: {updated_average_rating_count}권\n'
                '- 추천 데이터: 다음 서버 시작 시 자동 재구축\n'
            )
        )

    def resolve_json_path(self, given_path, file_name):
        if given_path:
            path = Path(given_path)
            if path.exists():
                return path
            raise CommandError(f'지정한 JSON 파일을 찾을 수 없습니다: {path}')

        base_dir = Path(settings.BASE_DIR)

        candidates = [
            base_dir / file_name,
            base_dir / 'data' / file_name,
            base_dir / 'fixtures' / file_name,
            base_dir / 'books' / 'fixtures' / file_name,
            base_dir / 'books' / file_name,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        candidate_text = '\n'.join(str(candidate) for candidate in candidates)
        raise CommandError(
            f'{file_name} 파일을 찾지 못했습니다.\n'
            f'아래 후보 경로 중 하나에 두거나, 명령어 옵션으로 직접 지정하세요.\n'
            f'{candidate_text}'
        )

    def load_fixture(self, path):
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise CommandError(f'{path} 파일의 최상위 구조는 list여야 합니다.')

        return data

    def validate_fixture_models(self, items, expected_model, path):
        for index, item in enumerate(items[:5]):
            if item.get('model') != expected_model:
                raise CommandError(
                    f'{path} 파일의 {index}번째 데이터 model 값이 예상과 다릅니다. '
                    f'예상: {expected_model}, 실제: {item.get("model")}'
                )

    def create_users(self):
        User = get_user_model()
        users = []

        for i in range(51):
            username = f'user{i:02d}'
            email = f'{username}@ssafy.com'

            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'bio': '',
                },
            )

            user.username = username
            user.bio = f'{username}의 더미 프로필입니다.'
            user.set_password('ssafy')
            user.save()

            users.append(user)

        return users

    def reset_dummy_user_data(self, users):
        ReviewLike.objects.filter(user__in=users).delete()
        ReviewLike.objects.filter(review__user__in=users).delete()
        Wishlist.objects.filter(user__in=users).delete()
        Collection.objects.filter(user__in=users).delete()
        Review.objects.filter(user__in=users).delete()
        Follow.objects.filter(from_user__in=users, to_user__in=users).delete()
        UserGenre.objects.filter(user__in=users).delete()
        CommentLike.objects.filter(user__in=users).delete()
        CommentLike.objects.filter(comment__user__in=users).delete()
        ThreadLike.objects.filter(user__in=users).delete()
        ThreadLike.objects.filter(thread__user__in=users).delete()
        Comment.objects.filter(user__in=users).delete()
        Thread.objects.filter(user__in=users).delete()

        self.stdout.write(
            self.style.WARNING('더미 유저의 기존 관계/활동 데이터를 초기화했습니다.')
        )

    def create_genres(self, genre_items):
        genre_by_fixture_pk = {}

        for item in genre_items:
            fixture_pk = item['pk']
            fields = item['fields']
            name = fields['name'].strip()

            genre, _ = Genre.objects.get_or_create(name=name)
            genre_by_fixture_pk[fixture_pk] = genre

        return genre_by_fixture_pk

    def create_books(self, book_items):
        book_by_fixture_pk = {}

        for item in book_items:
            fixture_pk = item['pk']
            fields = item['fields']

            published_date = datetime.strptime(
                fields['published_date'],
                '%Y-%m-%d',
            ).date()

            book, _ = Book.objects.update_or_create(
                isbn=fields['isbn'],
                defaults={
                    'title': fields['title'],
                    'author': fields['author'],
                    'publisher': fields['publisher'],
                    'description': fields['description'],
                    'cover_image': fields['cover_image'],
                    'published_date': published_date,
                },
            )

            book_by_fixture_pk[fixture_pk] = book

        return book_by_fixture_pk

    def create_book_genres(self, book_genre_items, book_by_fixture_pk, genre_by_fixture_pk):
        created_or_existing_count = 0

        for item in book_genre_items:
            fields = item['fields']
            book_fixture_pk = fields['book']
            genre_fixture_pk = fields['genre']

            book = book_by_fixture_pk.get(book_fixture_pk)
            genre = genre_by_fixture_pk.get(genre_fixture_pk)

            if book is None:
                raise CommandError(f'BookGenre가 참조하는 book pk={book_fixture_pk}를 찾지 못했습니다.')

            if genre is None:
                raise CommandError(f'BookGenre가 참조하는 genre pk={genre_fixture_pk}를 찾지 못했습니다.')

            BookGenre.objects.get_or_create(book=book, genre=genre)
            created_or_existing_count += 1

        return created_or_existing_count

    def create_user_genres(self, users):
        genre_by_name = {
            genre.name: genre
            for genre in Genre.objects.all()
        }

        created_count = 0

        for index, user in enumerate(users):
            pattern = PREFERRED_GENRE_PATTERNS[index % len(PREFERRED_GENRE_PATTERNS)]

            for genre_name in pattern:
                genre = genre_by_name.get(genre_name)

                if genre is None:
                    continue

                _, created = UserGenre.objects.get_or_create(
                    user=user,
                    genre=genre,
                )

                if created:
                    created_count += 1

        return created_count

    def create_follows(self, users):
        created_count = 0
        user_count = len(users)
        popular_user_indexes = [0, 10, 20, 30, 40]

        for index, from_user in enumerate(users):
            target_indexes = set()

            target_indexes.add((index + 1) % user_count)
            target_indexes.add((index + 2) % user_count)
            target_indexes.add((index + 7) % user_count)
            target_indexes.add((index + 20) % user_count)
            target_indexes.add((index + 30) % user_count)
            target_indexes.add((index + 40) % user_count)
            target_indexes.add((index + 50) % user_count)

            same_pattern_indexes = [
                other_index
                for other_index in range(user_count)
                if other_index != index
                and other_index % len(PREFERRED_GENRE_PATTERNS)
                == index % len(PREFERRED_GENRE_PATTERNS)
            ]

            target_indexes.update(same_pattern_indexes[:2])
            target_indexes.add(popular_user_indexes[index % len(popular_user_indexes)])
            target_indexes.discard(index)

            for target_index in target_indexes:
                to_user = users[target_index]

                try:
                    _, created = Follow.objects.get_or_create(
                        from_user=from_user,
                        to_user=to_user,
                    )
                except IntegrityError:
                    continue

                if created:
                    created_count += 1

        return created_count

    def get_latest_books(self, latest_pool_size):
        latest_books = list(
            Book.objects.order_by('-published_date', 'id')[:latest_pool_size]
        )

        if not latest_books:
            raise CommandError('리뷰/위시리스트/컬렉션을 생성할 책 데이터가 없습니다.')

        return latest_books

    def create_reviews(self, users, latest_books, reviews_per_user, rng):
        created_count = 0
        updated_count = 0

        sample_size = min(reviews_per_user, len(latest_books))

        for user in users:
            selected_books = rng.sample(latest_books, sample_size)

            for book in selected_books:
                rating = rng.randint(1, 5)

                _, created = Review.objects.update_or_create(
                    user=user,
                    book=book,
                    defaults={
                        'rating': rating,
                        'content': (
                            f'{user.username}이(가) "{book.title}"을(를) 읽고 남긴 '
                            f'추천 알고리즘 테스트용 더미 리뷰입니다.'
                        ),
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        return created_count, updated_count

    def create_wishlists_and_collections(self, users, latest_books, rng):
        created_wishlists = 0
        skipped_wishlists = 0
        created_collections = 0
        skipped_collections = 0

        for user in users:
            shuffled_books = list(latest_books)
            rng.shuffle(shuffled_books)

            wishlist_count = rng.randint(50, 100)
            collection_count = rng.randint(50, 100)

            wishlist_books = shuffled_books[:wishlist_count]
            collection_books = shuffled_books[
                wishlist_count:wishlist_count + collection_count
            ]

            for book in wishlist_books:
                if Collection.objects.filter(user=user, book=book).exists():
                    skipped_wishlists += 1
                    continue

                try:
                    _, created = Wishlist.objects.get_or_create(
                        user=user,
                        book=book,
                    )
                except IntegrityError:
                    skipped_wishlists += 1
                    continue

                if created:
                    created_wishlists += 1
                else:
                    skipped_wishlists += 1

            for book in collection_books:
                if Wishlist.objects.filter(user=user, book=book).exists():
                    skipped_collections += 1
                    continue

                try:
                    _, created = Collection.objects.get_or_create(
                        user=user,
                        book=book,
                    )
                except IntegrityError:
                    skipped_collections += 1
                    continue

                if created:
                    created_collections += 1
                else:
                    skipped_collections += 1

        return (
            created_wishlists,
            skipped_wishlists,
            created_collections,
            skipped_collections,
        )

    def create_community_data(
        self,
        *,
        users,
        latest_books,
        threads_per_user,
        comments_per_thread,
        thread_likes_min,
        thread_likes_max,
        comment_likes_min,
        comment_likes_max,
        rng,
    ):
        threads_per_user = max(1, threads_per_user)
        comments_per_thread = max(0, comments_per_thread)
        thread_likes_min, thread_likes_max = self.normalize_like_range(
            thread_likes_min,
            thread_likes_max,
        )
        comment_likes_min, comment_likes_max = self.normalize_like_range(
            comment_likes_min,
            comment_likes_max,
        )

        # 이 커맨드가 만든 게시글은 매번 지우고 다시 만듭니다.
        # reset 옵션 없이 재실행해도 커뮤니티 더미데이터가 중복 누적되지 않게 하기 위함입니다.
        Thread.objects.filter(
            user__in=users,
            title__startswith='[더미]',
        ).delete()

        created_thread_count = 0
        created_comment_count = 0
        created_thread_like_count = 0
        skipped_thread_like_count = 0
        created_comment_like_count = 0
        skipped_comment_like_count = 0

        created_comments = []

        for user_index, user in enumerate(users):
            for thread_index in range(threads_per_user):
                book = rng.choice(latest_books)
                number = user_index * threads_per_user + thread_index + 1

                thread = Thread.objects.create(
                    user=user,
                    title=rng.choice(THREAD_TITLE_TEMPLATES).format(
                        book_title=book.title,
                        number=number,
                    ),
                    content=rng.choice(THREAD_CONTENT_TEMPLATES).format(
                        book_title=book.title,
                    ),
                )
                created_thread_count += 1

                for like_user in self.sample_users_for_likes(
                    users=users,
                    excluded_user=user,
                    min_count=thread_likes_min,
                    max_count=thread_likes_max,
                    rng=rng,
                ):
                    try:
                        _, created = ThreadLike.objects.get_or_create(
                            user=like_user,
                            thread=thread,
                        )
                    except IntegrityError:
                        skipped_thread_like_count += 1
                        continue

                    if created:
                        created_thread_like_count += 1
                    else:
                        skipped_thread_like_count += 1

                comment_candidates = [
                    candidate
                    for candidate in users
                    if candidate.pk != user.pk
                ]

                for _ in range(comments_per_thread):
                    comment_user = rng.choice(comment_candidates or users)
                    comment_book = rng.choice(latest_books)

                    comment = Comment.objects.create(
                        user=comment_user,
                        thread=thread,
                        content=rng.choice(COMMENT_CONTENT_TEMPLATES).format(
                            book_title=comment_book.title,
                        ),
                    )
                    created_comments.append(comment)
                    created_comment_count += 1

        for comment in created_comments:
            for like_user in self.sample_users_for_likes(
                users=users,
                excluded_user=comment.user,
                min_count=comment_likes_min,
                max_count=comment_likes_max,
                rng=rng,
            ):
                try:
                    _, created = CommentLike.objects.get_or_create(
                        user=like_user,
                        comment=comment,
                    )
                except IntegrityError:
                    skipped_comment_like_count += 1
                    continue

                if created:
                    created_comment_like_count += 1
                else:
                    skipped_comment_like_count += 1

        return {
            'threads': created_thread_count,
            'comments': created_comment_count,
            'thread_likes': created_thread_like_count,
            'skipped_thread_likes': skipped_thread_like_count,
            'comment_likes': created_comment_like_count,
            'skipped_comment_likes': skipped_comment_like_count,
        }

    def normalize_like_range(self, min_count, max_count):
        min_count = max(0, min_count)
        max_count = max(0, max_count)

        if max_count < min_count:
            max_count = min_count

        return min_count, max_count

    def sample_users_for_likes(self, *, users, excluded_user, min_count, max_count, rng):
        candidates = [
            user
            for user in users
            if user.pk != excluded_user.pk
        ]

        if not candidates or max_count <= 0:
            return []

        upper_bound = min(max_count, len(candidates))
        lower_bound = min(min_count, upper_bound)
        like_count = rng.randint(lower_bound, upper_bound)

        return rng.sample(candidates, like_count)

    def update_book_average_ratings(self):
        updated_count = 0

        books_with_reviews = (
            Book.objects
            .filter(reviews__isnull=False)
            .annotate(calculated_average_rating=Avg('reviews__rating'))
            .distinct()
        )

        for book in books_with_reviews:
            book.average_rating = round(book.calculated_average_rating, 2)
            book.save(update_fields=['average_rating'])
            updated_count += 1

        return updated_count
