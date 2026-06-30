from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from books.models import Book, Collection, Review, Wishlist

from .serializers import (
    SignUpSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    _book_data,
)


class ProfileBookDataTests(TestCase):
    def test_book_data_includes_bookshelf_back_statistics(self):
        user_model = get_user_model()
        first_user = user_model.objects.create_user(
            email='first@example.com',
            username='first',
            password='test-password',
        )
        second_user = user_model.objects.create_user(
            email='second@example.com',
            username='second',
            password='test-password',
        )
        book = Book.objects.create(
            title='통계 책',
            author='작가',
            publisher='출판사',
            isbn='9780000000001',
            description='설명',
            cover_image='https://example.com/cover.jpg',
            published_date=date(2026, 1, 1),
        )
        Review.objects.create(user=first_user, book=book, content='좋아요', rating=4)
        Review.objects.create(user=second_user, book=book, content='아주 좋아요', rating=5)
        Wishlist.objects.create(user=first_user, book=book)
        Wishlist.objects.create(user=second_user, book=book)
        Collection.objects.create(user=first_user, book=book)

        book.refresh_from_db()
        data = _book_data(book)

        self.assertEqual(data['average_rating'], 4.5)
        self.assertEqual(data['review_count'], 2)
        self.assertEqual(data['wishlist_count'], 2)
        self.assertEqual(data['collection_count'], 1)

        profile_data = UserProfileSerializer(first_user).data
        profile_book = profile_data['reviews'][0]['book']

        self.assertEqual(profile_book['average_rating'], 4.5)
        self.assertEqual(profile_book['review_count'], 2)
        self.assertEqual(profile_book['wishlist_count'], 2)
        self.assertEqual(profile_book['collection_count'], 1)
        self.assertEqual(profile_book['global_average_rating'], 4.5)
        self.assertEqual(profile_book['global_review_count'], 2)
        self.assertEqual(profile_book['global_wishlist_count'], 2)
        self.assertEqual(profile_book['global_collection_count'], 1)


class ProfilePasswordValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='reader@example.com',
            username='reader-profile',
            password='current-password',
        )

    def password_error(self, new_password):
        serializer = UserProfileUpdateSerializer(
            self.user,
            data={
                'current_password': 'current-password',
                'new_password': new_password,
            },
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        return str(serializer.errors['non_field_errors'][0])

    def test_short_password_error_is_korean(self):
        self.assertEqual(
            self.password_error('짧음'),
            '비밀번호는 최소 8자 이상이어야 합니다.',
        )

    def test_numeric_password_error_is_korean(self):
        self.assertEqual(
            self.password_error('123456789'),
            '숫자로만 이루어진 비밀번호는 사용할 수 없습니다.',
        )

    def test_common_password_error_is_korean(self):
        self.assertEqual(
            self.password_error('password'),
            '너무 흔하게 사용되는 비밀번호입니다. 다른 비밀번호를 입력해 주세요.',
        )


class SignUpValidationTests(TestCase):
    def first_error(self, data):
        serializer = SignUpSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        for errors in serializer.errors.values():
            return str(errors[0])
        return ''

    def test_required_field_errors_are_korean(self):
        self.assertEqual(
            self.first_error({}),
            '닉네임을 입력해 주세요.',
        )

    def test_invalid_email_error_is_korean(self):
        self.assertEqual(
            self.first_error({
                'username': '독자',
                'email': 'invalid-email',
                'password': 'safe-password-123',
            }),
            '올바른 이메일 형식으로 입력해 주세요.',
        )

    def test_signup_password_error_is_korean(self):
        self.assertEqual(
            self.first_error({
                'username': '독자',
                'email': 'reader2@example.com',
                'password': '12345678',
            }),
            '숫자로만 이루어진 비밀번호는 사용할 수 없습니다.',
        )

    def test_email_availability_reports_existing_email(self):
        get_user_model().objects.create_user(
            username='existing-user',
            email='existing@example.com',
            password='safe-password-123',
        )

        response = self.client.get(
            reverse('accounts:email_availability'),
            {'email': 'EXISTING@example.com'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['available'])
        self.assertEqual(
            response.json()['message'],
            '이미 사용 중인 이메일입니다.',
        )

    def test_email_availability_reports_available_email(self):
        response = self.client.get(
            reverse('accounts:email_availability'),
            {'email': 'available@example.com'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['available'])
