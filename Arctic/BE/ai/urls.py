from django.urls import path

from . import views

urlpatterns = [
    path('recommendations/', views.recommendations),
    path('analyze_reviews/<int:book_pk>/', views.analyze_reviews),
    path('ask_story_seeds/', views.ask_story_seeds),
    path('generate_ideas/', views.generate_ideas),
    path('suggest_plot/', views.suggest_plot),
    path('correct_text/', views.correct_text),
    path('writing_logs/', views.writing_logs),
    path('drafts/', views.drafts),
    path('drafts/<int:pk>/', views.draft_detail),
    path('drafts/<int:pk>/like/', views.draft_like_toggle),
    path('drafts/<int:pk>/comments/', views.draft_comments),
    path('comments/<int:comment_pk>/', views.draft_comment_detail),
    path('comments/<int:comment_pk>/like/', views.draft_comment_like_toggle),
]
