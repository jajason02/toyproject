from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from books.models import Book, BookStat

from .models import RecommendationCache
from .services.recommendation import _regression


def feature_row(
    *,
    preferred=0,
    item_genre=0,
    following_review=0,
    book_rating=0,
    author=0,
    genre_rating=3,
    genre_confidence=0,
    author_rating=3,
    author_confidence=0,
    liked_genre=0,
    disliked_genre=0,
):
    return [
        preferred,
        item_genre,
        following_review,
        0,
        0,
        book_rating / 5,
        0,
        author,
        genre_rating / 5,
        genre_confidence,
        author_rating / 5,
        author_confidence,
        liked_genre,
        disliked_genre,
        int(genre_confidence > 0),
        int(author_confidence > 0),
    ]


class ExpectedRatingTests(SimpleTestCase):
    def test_positive_genre_and_author_signals_raise_expected_rating(self):
        neutral = feature_row()
        positive = feature_row(
            preferred=1,
            item_genre=0.8,
            following_review=0.9,
            book_rating=4.5,
            author=1,
            genre_rating=4.5,
            genre_confidence=0.8,
            author_rating=5,
            author_confidence=0.7,
            liked_genre=0.8,
        )

        neutral_rating, positive_rating = _regression(
            [],
            [neutral, positive],
        )

        self.assertGreater(positive_rating, neutral_rating)
        self.assertGreaterEqual(positive_rating, 4.0)

    def test_recommended_candidate_rating_does_not_fall_below_three(self):
        low_rated_row = feature_row(
            author=-1,
            genre_rating=1,
            genre_confidence=1,
            author_rating=1,
            author_confidence=1,
            disliked_genre=1,
        )
        rating_rows = [
            (feature_row(), 1),
            (feature_row(), 2),
        ]

        [predicted] = _regression(rating_rows, [low_rated_row])

        self.assertEqual(predicted, 3.0)

    @patch('sklearn.ensemble.RandomForestRegressor')
    def test_low_model_output_is_used_as_relative_adjustment(
        self,
        regressor_class,
    ):
        regressor_class.return_value.predict.return_value = [1.2]
        rating_rows = [
            (feature_row(), 1),
            (feature_row(), 2),
            (feature_row(), 1),
            (feature_row(), 2),
            (feature_row(), 1),
        ]
        candidate = feature_row(
            preferred=1,
            item_genre=1,
            book_rating=4.5,
            liked_genre=1,
        )

        [predicted] = _regression(rating_rows, [candidate])

        self.assertGreaterEqual(predicted, 3.0)


class CachedRecommendationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email='cache@example.com',
            username='cache-reader',
            password='test-password',
        )
        cls.book = Book.objects.create(
            title='미리 계산된 추천 도서',
            author='추천 작가',
            publisher='추천 출판사',
            isbn='9780000000001',
            description='추천 캐시 API 테스트용 도서',
            cover_image='https://example.com/cache.jpg',
            published_date=date(2026, 1, 1),
            average_rating=4.5,
        )
        BookStat.objects.create(
            book=cls.book,
            average_rating=4.5,
            review_count=10,
            wishlist_count=5,
            collection_count=3,
        )
        RecommendationCache.objects.create(
            user=cls.user,
            book=cls.book,
            rank=1,
            score=0.9,
            scores={'final_score': 0.9},
            reasons=['preferred_genre'],
            model_version='test',
        )

    @patch('ai.views.rebuild_user_recommendation_cache')
    def test_cached_request_does_not_recalculate_recommendations(
        self,
        rebuild_cache,
    ):
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/ai/recommendations/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Recommendation-Cache'], 'HIT')
        self.assertIn('recommendation;dur=', response['Server-Timing'])
        self.assertEqual(
            response.data['daily']['book']['id'],
            self.book.id,
        )
        rebuild_cache.assert_not_called()
