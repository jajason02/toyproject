from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Avg, Count
from django.db.utils import OperationalError, ProgrammingError
from rest_framework import serializers

from books.models import Collection, Genre, Review, Wishlist

from .models import UserGenre

from ai.models import WritingDraft


User = get_user_model()


def validate_password_in_korean(password, user=None):
    try:
        validate_password(password, user)
    except DjangoValidationError as error:
        errors_by_code = {
            item.code: item
            for item in error.error_list
        }
        messages = []

        if 'password_too_short' in errors_by_code:
            item = errors_by_code['password_too_short']
            min_length = (item.params or {}).get('min_length', 8)
            messages.append(
                f'비밀번호는 최소 {min_length}자 이상이어야 합니다.',
            )
        if 'password_entirely_numeric' in errors_by_code:
            messages.append(
                '숫자로만 이루어진 비밀번호는 사용할 수 없습니다.',
            )
        if 'password_too_common' in errors_by_code:
            messages.append(
                '너무 흔하게 사용되는 비밀번호입니다. 다른 비밀번호를 입력해 주세요.',
            )
        if 'password_too_similar' in errors_by_code:
            messages.append(
                '이메일이나 닉네임과 너무 비슷한 비밀번호는 사용할 수 없습니다.',
            )
        if not messages:
            messages.append('사용할 수 없는 비밀번호입니다.')

        raise serializers.ValidationError(messages)


def _related_count(user, related_name):
    related_manager = getattr(user, related_name, None)
    if related_manager is None:
        return 0
    try:
        return related_manager.count()
    except (OperationalError, ProgrammingError):
        return 0


def _book_statistics(book):
    review_statistics = Review.objects.filter(book_id=book.pk).aggregate(
        average_rating=Avg('rating'),
        review_count=Count('id'),
    )
    return {
        'average_rating': round(
            float(review_statistics['average_rating'] or 0),
            1,
        ),
        'review_count': review_statistics['review_count'],
        'wishlist_count': Wishlist.objects.filter(
            book_id=book.pk,
        ).values('user_id').distinct().count(),
        'collection_count': Collection.objects.filter(
            book_id=book.pk,
        ).values('user_id').distinct().count(),
    }


def _book_data(book, statistics=None):
    if statistics is None:
        statistics = _book_statistics(book)
    return {
        'id': book.pk,
        'title': book.title,
        'author': book.author,
        'cover_image': book.cover_image,
        **statistics,
        'global_average_rating': statistics['average_rating'],
        'global_review_count': statistics['review_count'],
        'global_wishlist_count': statistics['wishlist_count'],
        'global_collection_count': statistics['collection_count'],
    }


def _review_data(review, statistics=None):
    return {
        'id': review.pk,
        'book': _book_data(review.book, statistics),
        'rating': review.rating,
        'content': review.content,
        'created_at': review.created_at,
        'like_count': review.likes.count(),
    }


def _wishlist_data(wishlist, statistics=None):
    return {
        'id': wishlist.pk,
        'book': _book_data(wishlist.book, statistics),
        'created_at': wishlist.created_at,
    }


def _collection_data(collection, statistics=None):
    return {
        'id': collection.pk,
        'book': _book_data(collection.book, statistics),
        'created_at': collection.created_at,
    }


def _thread_data(thread):
    return {
        'id': thread.pk,
        'title': thread.title,
        'content': thread.content,
        'created_at': thread.created_at,
    }


def _draft_data(draft, request=None):
    try:
        like_count = draft.likes.count()
        comment_count = draft.comments.count()
        is_liked = (
            draft.likes.filter(user=request.user).exists()
            if request and request.user.is_authenticated
            else False
        )
    except Exception:
        like_count = 0
        comment_count = 0
        is_liked = False
    return {
        'id': draft.pk,
        'title': draft.title,
        'draft_type': draft.draft_type,
        'genre': draft.genre,
        'keywords': draft.keywords,
        'content': draft.content,
        'is_public': draft.is_public,
        'created_at': draft.created_at,
        'like_count': like_count,
        'comment_count': comment_count,
        'is_liked': is_liked,
    }


class SignUpSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=20,
        error_messages={
            'required': '닉네임을 입력해 주세요.',
            'blank': '닉네임을 입력해 주세요.',
            'max_length': '닉네임은 20자 이하로 입력해 주세요.',
        },
    )
    email = serializers.EmailField(
        error_messages={
            'required': '이메일을 입력해 주세요.',
            'blank': '이메일을 입력해 주세요.',
            'invalid': '올바른 이메일 형식으로 입력해 주세요.',
        },
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        error_messages={
            'required': '비밀번호를 입력해 주세요.',
            'blank': '비밀번호를 입력해 주세요.',
        },
    )
    preferred_genres = serializers.ListField(
        child=serializers.IntegerField(
            error_messages={
                'invalid': '장르 정보가 올바르지 않습니다.',
            },
        ),
        required=False,
        error_messages={
            'not_a_list': '장르 정보가 올바르지 않습니다.',
        },
    )

    def validate(self, attrs):
        password_user = User(
            username=attrs.get('username', ''),
            email=attrs.get('email', ''),
        )
        validate_password_in_korean(attrs['password'], password_user)
        return attrs

    def validate_username(self, username):
        username = username.strip()
        if not username:
            raise serializers.ValidationError('닉네임을 입력해 주세요.')
        return username

    def validate_email(self, email):
        email = email.strip().lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('이미 사용 중인 이메일입니다.')
        return email

    def validate_preferred_genres(self, genre_ids):
        self._validate_genre_ids(genre_ids)
        return genre_ids

    def create(self, validated_data):
        preferred_genres = validated_data.pop('preferred_genres', [])
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        self._update_preferred_genres(user, preferred_genres)
        return user

    def _validate_genre_ids(self, genre_ids):
        if not genre_ids:
            return

        unique_ids = set(genre_ids)
        found_count = Genre.objects.filter(id__in=unique_ids).count()
        if found_count != len(unique_ids):
            raise serializers.ValidationError('존재하지 않는 장르가 포함되어 있습니다.')

    def _update_preferred_genres(self, user, genre_ids):
        UserGenre.objects.bulk_create(
            [
                UserGenre(user=user, genre_id=genre_id)
                for genre_id in dict.fromkeys(genre_ids)
            ]
        )


class UserProfileSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    thread_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    wishlist_count = serializers.SerializerMethodField()
    collection_count = serializers.SerializerMethodField()
    preferred_genres = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    wishlists = serializers.SerializerMethodField()
    collections = serializers.SerializerMethodField()
    threads = serializers.SerializerMethodField()
    drafts = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'bio',
            'profile_image',
            'is_following',
            'follower_count',
            'following_count',
            'review_count',
            'thread_count',
            'comment_count',
            'wishlist_count',
            'collection_count',
            'preferred_genres',
            'reviews',
            'wishlists',
            'collections',
            'threads',
            'drafts',
        ]

    def get_follower_count(self, user):
        return user.followers.count()

    def get_is_following(self, user):
        request = self.context.get('request')
        if request is None or request.user == user:
            return False

        return user.followers.filter(from_user=request.user).exists()

    def get_profile_image(self, user):
        if not user.profile_image:
            return ''

        image_url = user.profile_image.url
        request = self.context.get('request')
        if request is None:
            return image_url
        return request.build_absolute_uri(image_url)

    def get_following_count(self, user):
        return user.followings.count()

    def get_review_count(self, user):
        return _related_count(user, 'reviews')

    def get_thread_count(self, user):
        return _related_count(user, 'threads')

    def get_comment_count(self, user):
        return _related_count(user, 'comments')

    def get_wishlist_count(self, user):
        return _related_count(user, 'wishlist_entries')

    def get_collection_count(self, user):
        return _related_count(user, 'collection_entries')

    def get_preferred_genres(self, user):
        try:
            return [
                {
                    'id': user_genre.genre_id,
                    'name': user_genre.genre.name,
                }
                for user_genre in user.preferred_genres.select_related('genre')
            ]
        except (OperationalError, ProgrammingError):
            return []

    def _get_book_statistics_map(self, user):
        if hasattr(self, '_book_statistics_cache'):
            return self._book_statistics_cache

        book_ids = set(
            user.reviews.values_list('book_id', flat=True)
        )
        book_ids.update(
            user.wishlist_entries.values_list('book_id', flat=True)
        )
        book_ids.update(
            user.collection_entries.values_list('book_id', flat=True)
        )

        statistics = {
            book_id: {
                'average_rating': 0.0,
                'review_count': 0,
                'wishlist_count': 0,
                'collection_count': 0,
            }
            for book_id in book_ids
        }

        for row in Review.objects.filter(
            book_id__in=book_ids,
        ).values('book_id').annotate(
            average_rating=Avg('rating'),
            review_count=Count('id'),
        ):
            statistics[row['book_id']].update({
                'average_rating': round(
                    float(row['average_rating'] or 0),
                    1,
                ),
                'review_count': row['review_count'],
            })

        for row in Wishlist.objects.filter(
            book_id__in=book_ids,
        ).values('book_id').annotate(
            wishlist_count=Count('user_id', distinct=True),
        ):
            statistics[row['book_id']]['wishlist_count'] = (
                row['wishlist_count']
            )

        for row in Collection.objects.filter(
            book_id__in=book_ids,
        ).values('book_id').annotate(
            collection_count=Count('user_id', distinct=True),
        ):
            statistics[row['book_id']]['collection_count'] = (
                row['collection_count']
            )

        self._book_statistics_cache = statistics
        return statistics

    def get_reviews(self, user):
        statistics = self._get_book_statistics_map(user)
        return [
            _review_data(review, statistics[review.book_id])
            for review in user.reviews.select_related('book')
        ]

    def get_wishlists(self, user):
        statistics = self._get_book_statistics_map(user)
        return [
            _wishlist_data(wishlist, statistics[wishlist.book_id])
            for wishlist in user.wishlist_entries.select_related('book')
        ]

    def get_collections(self, user):
        statistics = self._get_book_statistics_map(user)
        try:
            return [
                _collection_data(
                    collection,
                    statistics[collection.book_id],
                )
                for collection in user.collection_entries.select_related('book')
            ]
        except (OperationalError, ProgrammingError):
            return []

    def get_threads(self, user):
        threads = getattr(user, 'threads', None)
        if threads is None:
            return []
        try:
            return [_thread_data(thread) for thread in threads.all()]
        except (OperationalError, ProgrammingError):
            return []

    def get_drafts(self, user):
        request = self.context.get('request')
        try:
            qs = WritingDraft.objects.filter(user=user)
            if request is None or request.user != user:
                qs = qs.filter(is_public=True)
            return [_draft_data(d, request) for d in qs]
        except (OperationalError, ProgrammingError):
            return []


class UserListSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'profile_image',
            'is_following',
        ]

    def get_is_following(self, user):
        request = self.context.get('request')
        if request is None or request.user == user:
            return False

        return user.followers.filter(from_user=request.user).exists()

    def get_profile_image(self, user):
        if not user.profile_image:
            return ''

        image_url = user.profile_image.url
        request = self.context.get('request')
        if request is None:
            return image_url
        return request.build_absolute_uri(image_url)


class UserProfileUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=20, required=False)
    bio = serializers.CharField(required=False, allow_blank=True)
    profile_image = serializers.FileField(required=False)
    preferred_genres = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
    )
    current_password = serializers.CharField(required=False, write_only=True)
    new_password = serializers.CharField(required=False, write_only=True)

    def validate(self, attrs):
        genre_ids = attrs.get('preferred_genres')
        if genre_ids is not None:
            self._validate_genre_ids(genre_ids)

        self._validate_password_change(attrs)
        return attrs

    def update(self, user, validated_data):
        username = validated_data.get('username')
        bio = validated_data.get('bio')
        profile_image = validated_data.get('profile_image')
        preferred_genres = validated_data.get('preferred_genres')
        new_password = validated_data.get('new_password')

        if username is not None:
            user.username = username
        if bio is not None:
            user.bio = bio
        if profile_image is not None:
            user.profile_image = profile_image
        if new_password:
            user.set_password(new_password)

        user.save()
        if preferred_genres is not None:
            self._update_preferred_genres(user, preferred_genres)

        return user

    def _validate_password_change(self, attrs):
        current_password = attrs.get('current_password')
        new_password = attrs.get('new_password')

        if not current_password and not new_password:
            return

        if not current_password:
            raise serializers.ValidationError(
                {'error': '현재 비밀번호가 필요합니다.'}
            )
        if not new_password:
            raise serializers.ValidationError(
                {'error': '새 비밀번호가 필요합니다.'}
            )
        if not self.instance.check_password(current_password):
            raise serializers.ValidationError(
                {'error': '현재 비밀번호가 올바르지 않습니다.'}
            )

        validate_password_in_korean(new_password, self.instance)

    def _validate_genre_ids(self, genre_ids):
        if not genre_ids:
            return

        unique_ids = set(genre_ids)
        found_count = Genre.objects.filter(id__in=unique_ids).count()
        if found_count != len(unique_ids):
            raise serializers.ValidationError(
                {'error': '존재하지 않는 장르가 포함되어 있습니다.'}
            )

    def _update_preferred_genres(self, user, genre_ids):
        user.preferred_genres.all().delete()
        UserGenre.objects.bulk_create(
            [
                UserGenre(user=user, genre_id=genre_id)
                for genre_id in dict.fromkeys(genre_ids)
            ]
        )
