from django.conf import settings
from django.db import models


class WritingDraft(models.Model):
    DRAFT_TYPES = [
        ('idea', '아이디어'),
        ('plot', '플롯'),
        ('correction', '교정'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='drafts',
    )
    title = models.CharField(max_length=200, blank=True)
    draft_type = models.CharField(max_length=20, choices=DRAFT_TYPES)
    genre = models.CharField(max_length=50, blank=True)
    keywords = models.CharField(max_length=200, blank=True)
    content = models.JSONField()
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'AI_WRITING_DRAFT'
        ordering = ['-created_at']


class AIWritingLog(models.Model):
    REQUEST_TYPES = [
        ('idea', '아이디어 발상'),
        ('plot', '플롯 제안'),
        ('correction', '문장 교정'),
        ('analysis', '리뷰 감상 분석'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='writing_logs',
    )
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    input_text = models.TextField()
    output_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'AI_WRITING_LOG'
        ordering = ['-created_at']


class CreationLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='creation_likes',
    )
    draft = models.ForeignKey(
        WritingDraft,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'AI_CREATION_LIKE'
        unique_together = ('user', 'draft')


class CreationComment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='creation_comments',
    )
    draft = models.ForeignKey(
        WritingDraft,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'AI_CREATION_COMMENT'
        ordering = ['created_at']


class CreationCommentLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='creation_comment_likes',
    )
    comment = models.ForeignKey(
        CreationComment,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'AI_CREATION_COMMENT_LIKE'
        unique_together = ('user', 'comment')


class DailyBookRecommendation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_book_recommendations',
    )
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.CASCADE,
        related_name='daily_recommendations',
    )
    recommendation_date = models.DateField()
    scores = models.JSONField(default=dict)
    candidate_sources = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'DAILY_BOOK_RECOMMENDATION'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recommendation_date'],
                name='unique_user_daily_book_recommendation',
            ),
        ]


class UserPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendation_preference',
    )
    average_rating = models.FloatField(default=3.0)
    genre_weights = models.JSONField(default=dict)
    liked_genres = models.JSONField(default=dict)
    disliked_genres = models.JSONField(default=dict)
    genre_average_ratings = models.JSONField(default=dict)
    genre_rating_counts = models.JSONField(default=dict)
    author_weights = models.JSONField(default=dict)
    author_average_ratings = models.JSONField(default=dict)
    author_rating_counts = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'USER_PREFERENCE'


class RecommendationCache(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cached_book_recommendations',
    )
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.CASCADE,
        related_name='recommendation_cache_entries',
    )
    rank = models.PositiveIntegerField()
    score = models.FloatField(default=0)
    scores = models.JSONField(default=dict)
    reasons = models.JSONField(default=list)
    model_version = models.CharField(max_length=64, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RECOMMENDATION_CACHE'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'book'],
                name='unique_user_book_recommendation_cache',
            ),
            models.UniqueConstraint(
                fields=['user', 'rank'],
                name='unique_user_recommendation_rank',
            ),
        ]
        indexes = [
            models.Index(
                fields=['user', 'rank'],
                name='recommend_user_rank_idx',
            ),
        ]


class RecommendationState(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendation_state',
    )
    is_dirty = models.BooleanField(default=True)
    dirty_reason = models.CharField(max_length=64, blank=True)
    last_built_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RECOMMENDATION_STATE'
