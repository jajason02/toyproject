from django.urls import path

from . import views


urlpatterns = [
    path('threads/', views.thread_list_create, name='thread-list-create'),
    path(
        'threads/<int:thread_pk>/',
        views.thread_detail_update_delete,
        name='thread-detail-update-delete',
    ),
    path(
        'threads/<int:thread_pk>/like/',
        views.thread_like_toggle,
        name='thread-like-toggle',
    ),
    path(
        'threads/<int:thread_pk>/comments/',
        views.comment_create,
        name='comment-create',
    ),
    path(
        'threads/<int:thread_pk>/comments/<int:comment_pk>/',
        views.comment_update_delete,
        name='comment-update-delete',
    ),
    path(
        'threads/<int:thread_pk>/comments/<int:comment_pk>/like/',
        views.comment_like_toggle,
        name='comment-like-toggle',
    ),
]
