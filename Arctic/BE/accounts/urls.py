from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path(
        'email-availability/',
        views.email_availability,
        name='email_availability',
    ),
    path('login/', views.cookie_login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('follow/<int:user_id>/', views.follow_toggle, name='follow_toggle'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_update, name='profile_update'),
    path('profile/followers/', views.follower_list, name='follower_list'),
    path('profile/following/', views.following_list, name='following_list'),
    path('profile/<int:user_id>/', views.profile, name='user_profile'),
    path('profile/<int:user_id>/followers/', views.follower_list, name='user_follower_list'),
    path('profile/<int:user_id>/following/', views.following_list, name='user_following_list'),
    path('users/search/', views.user_search, name='user_search'),
    path('token/refresh/', views.cookie_refresh, name='token_refresh'),
]
