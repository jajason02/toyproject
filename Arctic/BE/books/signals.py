from django.db.models import Avg
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review


def update_book_average_rating(book):
    average_rating = book.reviews.aggregate(
        average=Avg('rating'),
    )['average']
    book.average_rating = average_rating or 0
    book.save(update_fields=['average_rating'])


@receiver(post_save, sender=Review)
def update_average_rating_on_review_save(sender, instance, **kwargs):
    update_book_average_rating(instance.book)


@receiver(post_delete, sender=Review)
def update_average_rating_on_review_delete(sender, instance, **kwargs):
    update_book_average_rating(instance.book)
