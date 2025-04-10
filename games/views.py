import json
import os
from datetime import datetime
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template

from .forms import GameCreationForm
from .models import Character, Favorite, Game, Location


def home(request):
    return render(request, 'games/home.html')

@login_required
def dashboard(request):
    games = Game.objects.filter(owner=request.user)
    # Simplification: ne pas charger les favoris
    return render(request, 'games/dashboard.html', {
        'games': games
    })

@login_required
def create_game(request):
    if request.method == 'POST':
        form = GameCreationForm(request.POST)
        if form.is_valid():
            # Création simplifiée du jeu
            game = form.save(commit=False)
            game.owner = request.user
            
            # Valeurs par défaut au lieu de la génération IA
            game.title = "Nouveau jeu"
            game.universe_description = "Description de l'univers à compléter"
            game.story_act1 = "Premier acte à compléter"
            game.story_act2 = "Deuxième acte à compléter"
            game.story_act3 = "Troisième acte à compléter"
            game.save()
            
            # Créer un personnage par défaut
            Character.objects.create(
                game=game,
                name="Personnage principal",
                role="Protagoniste",
                background="Histoire du personnage à compléter",
                abilities="Capacités à définir"
            )
            
            # Créer un lieu par défaut
            Location.objects.create(
                game=game,
                name="Lieu principal",
                description="Description du lieu à compléter"
            )
            
            messages.success(request, "Votre concept de jeu a été créé avec succès!")
            return redirect('game_detail', game_id=game.id)
    else:
        form = GameCreationForm()
    
    return render(request, 'games/create_game.html', {'form': form})

@login_required
def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id, owner=request.user)
    characters = Character.objects.filter(game=game)
    locations = Location.objects.filter(game=game)
    
    return render(request, 'games/game_detail.html', {
        'game': game,
        'characters': characters,
        'locations': locations,
        'is_favorited': False  # Valeur simplifiée
    })

@login_required
def random_game(request):
    # Fonction simplifiée sans IA
    messages.info(request, "La fonction de création aléatoire n'est pas disponible dans cette version.")
    return redirect('dashboard')

@login_required
def toggle_favorite(request, game_id):
    # Fonction simplifiée sans fonctionnalité de favoris
    messages.info(request, "La fonctionnalité favoris n'est pas disponible dans cette version.")
    
    # Rediriger vers la page précédente
    next_url = request.GET.get('next', 'dashboard')
    if next_url == 'game_detail':
        return redirect('game_detail', game_id=game_id)
    return redirect(next_url)

@login_required
def favorites(request):
    # Page simplifiée sans fonctionnalité de favoris
    return render(request, 'games/favorites.html', {'games': []})

@login_required
def export_game_pdf(request, game_id):
    # Fonction simplifiée sans génération PDF
    messages.info(request, "L'export PDF n'est pas disponible dans cette version.")
    return redirect('game_detail', game_id=game_id)

# Fonctions d'utilitaire vidées
def link_callback(uri, rel):
    """
    Fonction utilitaire pour PDF (désactivée)
    """
    return uri

def html_to_pdf(html_string, output, link_callback=None):
    """
    Fonction de conversion HTML en PDF (désactivée)
    """
    return True

def generate_game_content(genre, ambiance, keywords, references):
    """
    Fonction de génération de contenu via IA (désactivée)
    """
    # Retour de données factices
    return {
        "title": "Nouveau Jeu",
        "universe_description": "Un univers mystérieux à explorer.",
        "story_act1": "Le début de l'aventure...",
        "story_act2": "Le coeur de l'histoire...",
        "story_act3": "La conclusion épique...",
        "characters": [
            {
                "name": "Héros",
                "role": "Protagoniste principal",
                "background": "Origine inconnue",
                "abilities": "Détermination et courage"
            }
        ],
        "locations": [
            {
                "name": "Monde initial",
                "description": "Le point de départ de l'aventure"
            }
        ]
    }

def generate_image(prompt):
    """
    Fonction de génération d'image via IA (désactivée)
    """
    return None

def download_and_save_image(url, filename, subfolder):
    """
    Fonction pour télécharger et sauvegarder des images (désactivée)
    """
    return None