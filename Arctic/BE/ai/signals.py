import sys

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from accounts.models import Follow, UserGenre
from books.models import Collection, Review, Wishlist

from .services.precompute import (
    mark_users_dirty,
    rebuild_book_stats,
)


def _skip_automatic_refresh():
    return 'test' in sys.argv or 'seed_dummy_library' in sys.argv


def _refresh_book_stat(book_id):
    if book_id:
        rebuild_book_stats([book_id])


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def review_changed(sender, instance, **kwargs):
    if _skip_automatic_refresh():
        return
    _refresh_book_stat(instance.book_id)
    mark_users_dirty([instance.user_id], 'review_changed')


@receiver(post_save, sender=Wishlist)
@receiver(post_delete, sender=Wishlist)
def wishlist_changed(sender, instance, **kwargs):
    if _skip_automatic_refresh():
        return
    _refresh_book_stat(instance.book_id)
    mark_users_dirty([instance.user_id], 'wishlist_changed')


@receiver(post_save, sender=Collection)
@receiver(post_delete, sender=Collection)
def collection_changed(sender, instance, **kwargs):
    if _skip_automatic_refresh():
        return
    _refresh_book_stat(instance.book_id)
    mark_users_dirty([instance.user_id], 'collection_changed')


@receiver(post_save, sender=UserGenre)
@receiver(post_delete, sender=UserGenre)
def preferred_genre_changed(sender, instance, **kwargs):
    if _skip_automatic_refresh():
        return
    mark_users_dirty(
        [instance.user_id],
        'preferred_genre_changed',
    )


@receiver(post_save, sender=Follow)
@receiver(post_delete, sender=Follow)
def follow_changed(sender, instance, **kwargs):
    if _skip_automatic_refresh():
        return
    mark_users_dirty(
        [instance.from_user_id],
        'follow_changed',
    )
