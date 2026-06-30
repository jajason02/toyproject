from django.conf import settings
from django.db import models


class Thread(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='threads',
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'THREAD'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.title


class Comment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'COMMENT'
        ordering = ['created_at', 'id']


class CommentLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_likes',
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='likes',
    )

    class Meta:
        db_table = 'COMMENT_LIKE'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'comment'],
                name='unique_user_comment_like',
            ),
        ]


class ThreadLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='thread_likes',
    )
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name='likes',
    )

    class Meta:
        db_table = 'THREAD_LIKE'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'thread'],
                name='unique_user_thread_like',
            ),
        ]
