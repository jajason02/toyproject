import django.db.models.deletion
from django.db import migrations, models


def copy_user_genre_names_to_genres(apps, schema_editor):
    UserGenre = apps.get_model('accounts', 'UserGenre')
    Genre = apps.get_model('books', 'Genre')

    for user_genre in UserGenre.objects.all():
        genre = Genre.objects.filter(name=user_genre.name).first()
        if genre is None:
            user_genre.delete()
            continue

        user_genre.genre = genre
        user_genre.save(update_fields=['genre'])


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='profile_image',
            field=models.FileField(blank=True, upload_to='profile_images/'),
        ),
        migrations.AddField(
            model_name='usergenre',
            name='genre',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='books.genre',
            ),
        ),
        migrations.RunPython(
            copy_user_genre_names_to_genres,
            migrations.RunPython.noop,
        ),
        migrations.RemoveConstraint(
            model_name='usergenre',
            name='unique_user_genre',
        ),
        migrations.RemoveField(
            model_name='usergenre',
            name='name',
        ),
        migrations.AlterField(
            model_name='usergenre',
            name='genre',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='books.genre',
            ),
        ),
        migrations.AddConstraint(
            model_name='usergenre',
            constraint=models.UniqueConstraint(
                fields=('user', 'genre'),
                name='unique_user_genre',
            ),
        ),
    ]
