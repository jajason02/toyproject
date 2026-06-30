from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0002_reviewlike'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='book',
            table='BOOK',
        ),
        migrations.AlterModelTable(
            name='genre',
            table='GENRE',
        ),
        migrations.AlterModelTable(
            name='bookgenre',
            table='BOOK_GENRE',
        ),
        migrations.AlterModelTable(
            name='review',
            table='REVIEW',
        ),
        migrations.AlterModelTable(
            name='reviewlike',
            table='REVIEW_LIKE',
        ),
        migrations.AlterModelTable(
            name='wishlist',
            table='WISHLIST',
        ),
    ]
