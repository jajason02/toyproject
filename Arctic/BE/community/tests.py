from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Comment, Thread, ThreadLike


class ThreadApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='writer',
            email='writer@example.com',
            password='test-password',
        )
        cls.other_user = get_user_model().objects.create_user(
            username='reader',
            email='reader@example.com',
            password='test-password',
        )
        cls.old_thread = Thread.objects.create(
            user=cls.user,
            title='오래된 스레드',
            content='오래된 본문',
        )
        cls.new_thread = Thread.objects.create(
            user=cls.other_user,
            title='최신 스레드',
            content='최신 본문',
        )
        Comment.objects.create(
            user=cls.other_user,
            thread=cls.old_thread,
            content='댓글입니다.',
        )

    def test_thread_list_returns_latest_order(self):
        response = self.client.get(reverse('thread-list-create'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [thread['id'] for thread in response.data['results']],
            [self.new_thread.id, self.old_thread.id],
        )
        self.assertEqual(response.data['count'], 2)

    def test_thread_list_is_paginated_by_ten(self):
        Thread.objects.bulk_create([
            Thread(
                user=self.user,
                title=f'페이지 테스트 {index}',
                content='페이지네이션 본문',
            )
            for index in range(9)
        ])

        first_page = self.client.get(reverse('thread-list-create'))
        second_page = self.client.get(
            reverse('thread-list-create'),
            {'page': 2},
        )

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(len(first_page.data['results']), 10)
        self.assertEqual(first_page.data['count'], 11)
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.data['results']), 1)

    def test_thread_list_searches_title_content_or_both(self):
        title_match = Thread.objects.create(
            user=self.user,
            title='북극 검색어',
            content='관련 없는 본문',
        )
        content_match = Thread.objects.create(
            user=self.user,
            title='관련 없는 제목',
            content='본문에 북극 검색어가 있습니다.',
        )

        title_response = self.client.get(
            reverse('thread-list-create'),
            {'q': '북극', 'search_by': 'title'},
        )
        content_response = self.client.get(
            reverse('thread-list-create'),
            {'q': '북극', 'search_by': 'content'},
        )
        all_response = self.client.get(
            reverse('thread-list-create'),
            {'q': '북극', 'search_by': 'all'},
        )

        self.assertEqual(
            [thread['id'] for thread in title_response.data['results']],
            [title_match.id],
        )
        self.assertEqual(
            [thread['id'] for thread in content_response.data['results']],
            [content_match.id],
        )
        self.assertEqual(
            {thread['id'] for thread in all_response.data['results']},
            {title_match.id, content_match.id},
        )

    def test_authenticated_user_can_create_thread(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse('thread-list-create'),
            {'title': '새 스레드', 'content': '새 본문'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], '새 스레드')
        self.assertTrue(
            Thread.objects.filter(
                user=self.user,
                title='새 스레드',
            ).exists(),
        )

    def test_anonymous_user_cannot_create_thread(self):
        response = self.client.post(
            reverse('thread-list-create'),
            {'title': '새 스레드', 'content': '새 본문'},
            format='json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.data)

    def test_thread_detail_includes_comments_and_like_count(self):
        ThreadLike.objects.create(user=self.other_user, thread=self.old_thread)

        response = self.client.get(
            reverse('thread-detail-update-delete', args=[self.old_thread.id]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], self.old_thread.title)
        self.assertEqual(len(response.data['comments']), 1)
        self.assertEqual(response.data['like_count'], 1)
        self.assertFalse(response.data['is_liked'])

    def test_user_can_update_own_thread(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                'thread-detail-update-delete',
                args=[self.old_thread.id],
            ),
            {'title': '수정된 스레드'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.old_thread.refresh_from_db()
        self.assertEqual(self.old_thread.title, '수정된 스레드')

    def test_user_cannot_update_other_users_thread(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(
            reverse(
                'thread-detail-update-delete',
                args=[self.old_thread.id],
            ),
            {'title': '수정 실패'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)

    def test_user_can_delete_own_thread(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'thread-detail-update-delete',
                args=[self.old_thread.id],
            ),
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Thread.objects.filter(id=self.old_thread.id).exists())

    def test_other_user_can_toggle_thread_like(self):
        self.client.force_authenticate(user=self.other_user)

        like_response = self.client.post(
            reverse('thread-like-toggle', args=[self.old_thread.id]),
        )
        unlike_response = self.client.post(
            reverse('thread-like-toggle', args=[self.old_thread.id]),
        )

        self.assertEqual(like_response.status_code, 200)
        self.assertTrue(like_response.data['is_liked'])
        self.assertEqual(like_response.data['like_count'], 1)
        self.assertEqual(unlike_response.status_code, 200)
        self.assertFalse(unlike_response.data['is_liked'])
        self.assertEqual(unlike_response.data['like_count'], 0)

    def test_user_cannot_like_own_thread(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse('thread-like-toggle', args=[self.old_thread.id]),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_authenticated_user_can_create_comment(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse('comment-create', args=[self.old_thread.id]),
            {'content': '새 댓글입니다.'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['content'], '새 댓글입니다.')
        self.assertTrue(
            Comment.objects.filter(
                user=self.user,
                thread=self.old_thread,
                content='새 댓글입니다.',
            ).exists(),
        )

    def test_user_can_update_own_comment(self):
        comment = Comment.objects.create(
            user=self.user,
            thread=self.old_thread,
            content='수정 전 댓글입니다.',
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                'comment-update-delete',
                args=[self.old_thread.id, comment.id],
            ),
            {'content': '수정된 댓글입니다.'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.content, '수정된 댓글입니다.')

    def test_user_cannot_update_other_users_comment(self):
        comment = Comment.objects.create(
            user=self.user,
            thread=self.old_thread,
            content='다른 유저 댓글입니다.',
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(
            reverse(
                'comment-update-delete',
                args=[self.old_thread.id, comment.id],
            ),
            {'content': '수정 실패'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)

    def test_user_can_delete_own_comment(self):
        comment = Comment.objects.create(
            user=self.user,
            thread=self.old_thread,
            content='삭제할 댓글입니다.',
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'comment-update-delete',
                args=[self.old_thread.id, comment.id],
            ),
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())
