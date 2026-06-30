from datetime import date
from unittest.mock import patch

from accounts.models import Follow
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Book, BookGenre, Genre, Review, Wishlist


class BookApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fiction = Genre.objects.create(name='소설')
        cls.essay = Genre.objects.create(name='에세이')
        cls.older_book = Book.objects.create(
            title='평점 높은 책',
            author='작가 A',
            publisher='출판사 A',
            isbn='1111111111111',
            description='설명 A',
            cover_image='https://example.com/a.jpg',
            published_date=date(2025, 1, 1),
            average_rating=4.8,
        )
        cls.newer_book = Book.objects.create(
            title='최신 책',
            author='작가 B',
            publisher='출판사 B',
            isbn='2222222222222',
            description='설명 B',
            cover_image='https://example.com/b.jpg',
            published_date=date(2026, 1, 1),
            average_rating=3.5,
        )
        BookGenre.objects.create(book=cls.older_book, genre=cls.fiction)
        BookGenre.objects.create(book=cls.newer_book, genre=cls.essay)
        cls.user = get_user_model().objects.create_user(
            username='reader',
            password='test-password',
        )
        Review.objects.create(
            user=cls.user,
            book=cls.older_book,
            content='좋은 책입니다.',
            rating=5,
        )
        Wishlist.objects.create(user=cls.user, book=cls.older_book)

    def test_book_list_defaults_to_latest_order(self):
        response = self.client.get(reverse('book-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [book['id'] for book in response.data],
            [self.newer_book.id, self.older_book.id],
        )

    def test_book_list_filters_genre_and_orders_by_rating(self):
        response = self.client.get(
            reverse('book-list'),
            {'genre': self.fiction.id, 'ordering': 'rating'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.older_book.id)

    def test_book_list_rejects_invalid_ordering(self):
        response = self.client.get(reverse('book-list'), {'ordering': 'oldest'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_book_list_searches_by_title(self):
        response = self.client.get(reverse('book-list'), {'search': '평점'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.older_book.id)

    def test_book_list_searches_by_author(self):
        response = self.client.get(reverse('book-list'), {'search': '작가 B'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.newer_book.id)

    @patch('books.views.search_and_save_books')
    def test_book_list_does_not_call_aladin_when_db_result_exists(
        self,
        mock_search,
    ):
        response = self.client.get(reverse('book-list'), {'search': '평점'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        mock_search.assert_not_called()

    @patch('books.views.search_and_save_books')
    def test_book_list_calls_aladin_when_db_result_does_not_exist(
        self,
        mock_search,
    ):
        def create_aladin_book(query):
            book = Book.objects.create(
                title=f'{query} 알라딘 도서',
                author='알라딘 작가',
                publisher='알라딘 출판사',
                isbn='9999999999999',
                description='알라딘 설명',
                cover_image='https://example.com/aladin.jpg',
                published_date=date(2026, 6, 23),
            )
            BookGenre.objects.create(book=book, genre=self.fiction)
            return [book]

        mock_search.side_effect = create_aladin_book

        response = self.client.get(
            reverse('book-list'),
            {'search': '없는도서'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], '없는도서 알라딘 도서')
        mock_search.assert_called_once_with('없는도서')

    @patch('books.views.search_and_save_books')
    def test_book_list_does_not_call_aladin_with_genre_filter(
        self,
        mock_search,
    ):
        response = self.client.get(
            reverse('book-list'),
            {
                'search': '없는도서',
                'genre': self.fiction.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        mock_search.assert_not_called()

    def test_book_list_combines_search_genre_and_ordering(self):
        response = self.client.get(
            reverse('book-list'),
            {
                'search': '책',
                'genre': self.fiction.id,
                'ordering': 'rating',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.older_book.id)

    def test_book_detail_includes_reviews_and_anonymous_wishlist_status(self):
        response = self.client.get(
            reverse('book-detail', args=[self.older_book.id]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['average_rating'], 5.0)
        self.assertEqual(response.data['reviews'][0]['username'], 'reader')
        self.assertFalse(response.data['is_wishlisted'])

    def test_book_detail_includes_authenticated_wishlist_status(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('book-detail', args=[self.older_book.id]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_wishlisted'])

    def test_authenticated_user_can_create_review_and_average_updates(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse('review-create', args=[self.newer_book.id]),
            {'content': '새 리뷰입니다.', 'rating': 5},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['rating'], 5)
        self.newer_book.refresh_from_db()
        self.assertEqual(self.newer_book.average_rating, 5)

    def test_user_can_update_own_review_and_average_updates(self):
        review = Review.objects.get(user=self.user, book=self.older_book)
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                'review-update-delete',
                args=[self.older_book.id, review.id],
            ),
            {'rating': 3},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['rating'], 3)
        self.older_book.refresh_from_db()
        self.assertEqual(self.older_book.average_rating, 3)

    def test_user_can_delete_own_review_and_average_updates(self):
        review = Review.objects.get(user=self.user, book=self.older_book)
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'review-update-delete',
                args=[self.older_book.id, review.id],
            ),
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Review.objects.filter(id=review.id).exists())
        self.older_book.refresh_from_db()
        self.assertEqual(self.older_book.average_rating, 0)

    def test_other_user_can_toggle_review_like(self):
        review = Review.objects.get(user=self.user, book=self.older_book)
        other_user = get_user_model().objects.create_user(
            username='other',
            email='other@example.com',
            password='test-password',
        )
        self.client.force_authenticate(user=other_user)

        like_response = self.client.post(
            reverse('review-like-toggle', args=[review.id]),
        )
        unlike_response = self.client.post(
            reverse('review-like-toggle', args=[review.id]),
        )

        self.assertEqual(like_response.status_code, 200)
        self.assertTrue(like_response.data['is_liked'])
        self.assertEqual(like_response.data['like_count'], 1)
        self.assertEqual(unlike_response.status_code, 200)
        self.assertFalse(unlike_response.data['is_liked'])
        self.assertEqual(unlike_response.data['like_count'], 0)

    def test_user_can_toggle_wishlist(self):
        self.client.force_authenticate(user=self.user)

        add_response = self.client.post(
            reverse('wishlist-toggle', args=[self.newer_book.id]),
        )

        self.assertEqual(add_response.status_code, 200)
        self.assertTrue(add_response.data['is_wishlisted'])
        self.assertTrue(
            Wishlist.objects.filter(
                user=self.user,
                book=self.newer_book,
            ).exists(),
        )

        remove_response = self.client.post(
            reverse('wishlist-toggle', args=[self.newer_book.id]),
        )

        self.assertEqual(remove_response.status_code, 200)
        self.assertFalse(remove_response.data['is_wishlisted'])
        self.assertFalse(
            Wishlist.objects.filter(
                user=self.user,
                book=self.newer_book,
            ).exists(),
        )

    def test_user_can_list_own_wishlist(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('wishlist-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['book']['id'], self.older_book.id)

    def test_popular_book_list_returns_top_10_by_rating(self):
        for index in range(10):
            Book.objects.create(
                title=f'인기도서 {index}',
                author='작가',
                publisher='출판사',
                isbn=f'33333333333{index:02d}',
                description='설명',
                cover_image='https://example.com/popular.jpg',
                published_date=date(2026, 1, index + 1),
                average_rating=index,
            )

        response = self.client.get(reverse('popular-book-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 10)
        self.assertGreaterEqual(
            response.data[0]['average_rating'],
            response.data[-1]['average_rating'],
        )

    def test_following_review_feed_returns_followed_users_reviews(self):
        followed_user = get_user_model().objects.create_user(
            username='followed',
            email='followed@example.com',
            password='test-password',
        )
        not_followed_user = get_user_model().objects.create_user(
            username='not-followed',
            email='not-followed@example.com',
            password='test-password',
        )
        Follow.objects.create(from_user=self.user, to_user=followed_user)
        followed_review = Review.objects.create(
            user=followed_user,
            book=self.newer_book,
            content='팔로우한 유저의 리뷰입니다.',
            rating=4,
        )
        Review.objects.create(
            user=not_followed_user,
            book=self.newer_book,
            content='팔로우하지 않은 유저의 리뷰입니다.',
            rating=2,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('following-review-feed'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], followed_review.id)
        self.assertEqual(response.data[0]['book']['id'], self.newer_book.id)
