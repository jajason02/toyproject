# Generated manually for recommendation precomputation.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0006_creationcommentlike'),
        ('books', '0005_bookstat'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RecommendationState',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('is_dirty', models.BooleanField(default=True)),
                ('dirty_reason', models.CharField(blank=True, max_length=64)),
                ('last_built_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'user',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='recommendation_state',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'db_table': 'RECOMMENDATION_STATE',
            },
        ),
        migrations.CreateModel(
            name='UserPreference',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('average_rating', models.FloatField(default=3.0)),
                ('genre_weights', models.JSONField(default=dict)),
                ('liked_genres', models.JSONField(default=dict)),
                ('disliked_genres', models.JSONField(default=dict)),
                ('genre_average_ratings', models.JSONField(default=dict)),
                ('genre_rating_counts', models.JSONField(default=dict)),
                ('author_weights', models.JSONField(default=dict)),
                ('author_average_ratings', models.JSONField(default=dict)),
                ('author_rating_counts', models.JSONField(default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'user',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='recommendation_preference',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'db_table': 'USER_PREFERENCE',
            },
        ),
        migrations.CreateModel(
            name='RecommendationCache',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('rank', models.PositiveIntegerField()),
                ('score', models.FloatField(default=0)),
                ('scores', models.JSONField(default=dict)),
                ('reasons', models.JSONField(default=list)),
                ('model_version', models.CharField(blank=True, max_length=64)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'book',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='recommendation_cache_entries',
                        to='books.book',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='cached_book_recommendations',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'db_table': 'RECOMMENDATION_CACHE',
                'indexes': [
                    models.Index(
                        fields=['user', 'rank'],
                        name='recommend_user_rank_idx',
                    ),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('user', 'book'),
                        name='unique_user_book_recommendation_cache',
                    ),
                    models.UniqueConstraint(
                        fields=('user', 'rank'),
                        name='unique_user_recommendation_rank',
                    ),
                ],
            },
        ),
    ]
