from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_game, name='create_game'),
    path('random/', views.random_game, name='random_game'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
]