from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    # Регистрация и управление участниками
    path('tournament/<int:tournament_id>/register/', views.register_participant, name='register_participant'),
    path('tournament/<int:tournament_id>/participants/', views.participant_list, name='participant_list'),
    path('participant/<int:participant_id>/edit/', views.edit_participant, name='edit_participant'),
    path('participant/<int:participant_id>/delete/', views.delete_participant, name='delete_participant'),
    path('tournament/<int:tournament_id>/search/', views.search_participants, name='search_participants'),

    # Excel импорт
    path('tournament/<int:tournament_id>/upload-excel/', views.upload_excel, name='upload_excel'),
    path('tournament/<int:tournament_id>/download-template/', views.download_template, name='download_template'),

    # Категории и сетки
    path('tournament/<int:tournament_id>/categories/', views.category_list, name='category_list'),
    path('tournament/<int:tournament_id>/generate-all/', views.generate_all_brackets, name='generate_all_brackets'),

    # Просмотр конкретной категории
    path('tournament/<int:tournament_id>/bracket/<str:age_category>/<str:gender>/<str:weight_category>/',
         views.category_bracket, name='category_bracket'),
    path('tournament/<int:tournament_id>/bracket/<str:age_category>/<str:gender>/<str:weight_category>/generate/',
         views.generate_bracket_for_category_view, name='generate_bracket_for_category'),
    path('tournament/<int:tournament_id>/bracket/<str:age_category>/<str:gender>/<str:weight_category>/print/',
         views.print_bracket, name='print_bracket'),
    path('tournament/<int:tournament_id>/bracket/<str:age_category>/<str:gender>/<str:weight_category>/clear/',
         views.clear_category_matches, name='clear_category_matches'),

    # Матчи
    path('match/<int:match_id>/', views.match_detail, name='match_detail'),

    # Статистика
    path('tournament/<int:tournament_id>/stats/', views.tournament_stats, name='tournament_stats'),

    # API
    path('api/tournament/<int:tournament_id>/participants/', views.ajax_get_participants, name='api_participants'),
]