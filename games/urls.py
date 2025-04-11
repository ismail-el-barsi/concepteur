from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_game, name='create_game'),
    path('random/', views.random_game, name='random_game'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
    path('game/<int:game_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('game/<int:game_id>/export-pdf/', views.export_game_pdf, name='export_game_pdf'),
    path('favorites/', views.favorites, name='favorites'),
    path('game/<int:game_id>/narrative-choices/', views.narrative_choices, name='narrative_choices'),
    path('game/<int:game_id>/generate-choices/', views.generate_choices, name='generate_choices'),
    path('game/<int:game_id>/select-choice/<int:choice_id>/', views.select_choice, name='select_choice'),
]