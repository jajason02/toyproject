from rest_framework import serializers

from .models import Book, Collection, Genre, Review, ReviewLike, Wishlist


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('id', 'name')


class BookListSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    is_wishlisted = serializers.SerializerMethodField()
    is_collected = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            'id',
            'title',
            'author',
            'cover_image',
            'published_date',
            'average_rating',
            'genres',
            'is_wishlisted',
            'is_collected',
        )

    def get_is_wishlisted(self, book):
        wishlist_book_ids = self.context.get('wishlist_book_ids')
        if wishlist_book_ids is not None:
            return book.id in wishlist_book_ids
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return Wishlist.objects.filter(user=request.user, book=book).exists()

    def get_is_collected(self, book):
        collection_book_ids = self.context.get('collection_book_ids')
        if collection_book_ids is not None:
            return book.id in collection_book_ids
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return Collection.objects.filter(user=request.user, book=book).exists()


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    profile_image = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(source='likes.count', read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            'id',
            'user_id',
            'username',
            'profile_image',
            'content',
            'rating',
            'created_at',
            'like_count',
            'is_liked',
            'is_mine',
        )
        read_only_fields = ('id', 'user_id', 'username', 'profile_image', 'created_at')

    def get_profile_image(self, review):
        image = getattr(review.user, 'profile_image', None)
        if not image:
            return ''
        image_url = image.url
        request = self.context.get('request')
        if request is None:
            return image_url
        return request.build_absolute_uri(image_url)

    def get_is_liked(self, review):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return ReviewLike.objects.filter(
            user=request.user,
            review=review,
        ).exists()

    def get_is_mine(self, review):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return review.user_id == request.user.id


class BookDetailSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    is_wishlisted = serializers.SerializerMethodField()
    is_collected = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            'id',
            'title',
            'author',
            'publisher',
            'isbn',
            'description',
            'cover_image',
            'published_date',
            'average_rating',
            'genres',
            'reviews',
            'is_wishlisted',
            'is_collected',
        )

    def get_is_wishlisted(self, book):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return Wishlist.objects.filter(user=request.user, book=book).exists()

    def get_is_collected(self, book):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return Collection.objects.filter(user=request.user, book=book).exists()


class WishlistSerializer(serializers.ModelSerializer):
    book = BookListSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ('id', 'book', 'created_at')


class FeedReviewSerializer(ReviewSerializer):
    book = BookListSerializer(read_only=True)

    class Meta(ReviewSerializer.Meta):
        fields = ReviewSerializer.Meta.fields + ('book',)
