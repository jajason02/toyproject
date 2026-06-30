from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0003_dailybookrecommendation'),
    ]

    operations = [
        migrations.AddField(
            model_name='writingdraft',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
    ]
