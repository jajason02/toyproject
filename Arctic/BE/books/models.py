from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'GENRE'

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    cover_image = models.URLField(max_length=500)
    published_date = models.DateField()
    average_rating = models.FloatField(default=0)
    genres = models.ManyToManyField(
        Genre,
        through='BookGenre',
        related_name='books',
    )

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'BOOK'


class BookStat(models.Model):
    book = models.OneToOneField(
        Book,
        on_delete=models.CASCADE,
        related_name='stat',
    )
    average_rating = models.FloatField(default=0)
    review_count = models.PositiveIntegerField(default=0)
    wishlist_count = models.PositiveIntegerField(default=0)
    collection_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'BOOK_STAT'


class BookGenre(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)

    class Meta:
        db_table = 'BOOK_GENRE'
        constraints = [
            models.UniqueConstraint(
                fields=['book', 'genre'],
                name='unique_book_genre',
            ),
        ]


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    content = models.TextField()
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'REVIEW'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'book'],
                name='unique_user_book_review',
            ),
        ]


class ReviewLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_likes',
    )
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='likes',
    )

    class Meta:
        db_table = 'REVIEW_LIKE'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'review'],
                name='unique_user_review_like',
            ),
        ]


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_entries',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='wishlist_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'WISHLIST'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'book'],
                name='unique_user_book_wishlist',
            ),
        ]


class Collection(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collection_entries',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='collection_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'COLLECTION'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'book'],
                name='unique_user_book_collection',
            ),
        ]
