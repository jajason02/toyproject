from django.urls import path

from . import views


urlpatterns = [
    path('', views.book_list, name='book-list'),
    path('materialize/', views.book_materialize, name='book-materialize'),
    path('genres/', views.genre_list, name='genre-list'),
    path('popular/', views.popular_book_list, name='popular-book-list'),
    path('feed/', views.following_review_feed, name='following-review-feed'),
    path('wishlist/', views.wishlist_list, name='wishlist-list'),
    path('<int:book_pk>/cover/', views.book_cover, name='book-cover'),
    path('<int:book_pk>/', views.book_detail, name='book-detail'),
    path(
        '<int:book_pk>/wishlist/',
        views.wishlist_toggle,
        name='wishlist-toggle',
    ),
    path(
        '<int:book_pk>/collection/',
        views.collection_toggle,
        name='collection-toggle',
    ),
    path('<int:book_pk>/reviews/', views.review_create, name='review-create'),
    path(
        '<int:book_pk>/reviews/<int:review_pk>/',
        views.review_update_delete,
        name='review-update-delete',
    ),
    path(
        'reviews/<int:review_pk>/like/',
        views.review_like_toggle,
        name='review-like-toggle',
    ),
]
