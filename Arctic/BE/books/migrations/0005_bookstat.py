# Generated manually for recommendation precomputation.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0004_collection'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookStat',
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
                ('average_rating', models.FloatField(default=0)),
                ('review_count', models.PositiveIntegerField(default=0)),
                ('wishlist_count', models.PositiveIntegerField(default=0)),
                ('collection_count', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'book',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='stat',
                        to='books.book',
                    ),
                ),
            ],
            options={
                'db_table': 'BOOK_STAT',
            },
        ),
    ]
