from django.contrib.auth.models import AbstractUser
from django.db import models

from books.models import Genre


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=20)
    bio = models.TextField(blank=True)
    profile_image = models.FileField(
        upload_to='profile_images/',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'USER'


class Follow(models.Model):
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followings',
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'FOLLOW'
        constraints = [
            # 중복 팔로우 금지
            models.UniqueConstraint(
                fields=['from_user', 'to_user'],
                name='unique_follow',
            ),
            # 자기자신 팔로우 금지
            models.CheckConstraint(
                condition=~models.Q(from_user=models.F('to_user')),
                name='prevent_self_follow',
            ),
        ]


class UserGenre(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='preferred_genres',
    )
    genre = models.ForeignKey(
        Genre,
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = 'USER_GENRE'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'genre'],
                name='unique_user_genre',
            ),
        ]
