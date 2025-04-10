import json
import os

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from openai import OpenAI

from .forms import GameCreationForm as GameForm
from .forms import LocationForm
from .models import Character, Game, Location


def home(request):
    return render(request, 'games/home.html')

@login_required
def dashboard(request):
    games = Game.objects.filter(owner=request.user)
    
    return render(request, 'games/dashboard.html', {
        'games': games,
    })

@login_required
def create_game(request):
    if request.method == 'POST':
        form = GameForm(request.POST)
        if form.is_valid():
            # Créer le jeu sans sauvegarder
            game = form.save(commit=False)
            game.owner = request.user
            
            # Récupérer les informations du formulaire
            genre = form.cleaned_data['genre']
            ambiance = form.cleaned_data['ambiance']
            keywords = form.cleaned_data['keywords']
            references = form.cleaned_data.get('references', '')
            
            # Génération du contenu avec l'API OpenAI (ChatGPT)
            game_data = generate_game_content(genre, ambiance, keywords, references)
            
            if game_data:
                # Mise à jour des champs du jeu
                game.title = game_data.get('title', 'Untitled Game')
                game.universe_description = game_data.get('universe_description', '')
                game.story_act1 = game_data.get('story_act1', '')
                game.story_act2 = game_data.get('story_act2', '')
                game.story_act3 = game_data.get('story_act3', '')
                game.save()
                
                # Création des personnages et génération de leurs images
                characters = game_data.get('characters', [])
                for char_data in characters:
                    character = Character(
                        game=game,
                        name=char_data.get('name', 'Unknown Character'),
                        role=char_data.get('role', 'Unknown Role'),
                        background=char_data.get('background', ''),
                        abilities=char_data.get('abilities', '')
                    )
                    
                    # Générer une image pour le personnage avec DALL-E
                    character_prompt = f"Portrait of {character.name}, a {character.role} from a {game.genre_name} game with {game.ambiance_name} ambiance."
                    image_url = generate_image(character_prompt)
                    if image_url:
                        # Télécharger et sauvegarder l'image
                        character.image = download_and_save_image(image_url, f"character_{character.name}.jpg", "characters")
                    
                    character.save()
                
                # Création des lieux et génération de leurs images
                locations = game_data.get('locations', [])
                for loc_data in locations:
                    location = Location(
                        game=game,
                        name=loc_data.get('name', 'Unknown Location'),
                        description=loc_data.get('description', '')
                    )
                    
                    # Générer une image pour le lieu avec DALL-E
                    location_prompt = f"{location.name} from a {game.genre_name} game with {game.ambiance_name} ambiance, {game.title}."
                    image_url = generate_image(location_prompt)
                    if image_url:
                        # Télécharger et sauvegarder l'image
                        location.image = download_and_save_image(image_url, f"location_{location.name}.jpg", "locations")
                    
                    location.save()
                
                messages.success(request, "Votre concept de jeu a été généré avec succès!")
                return redirect('game_detail', game_id=game.id)
            else:
                messages.error(request, "Erreur lors de la génération du contenu du jeu.")
    else:
        form = GameForm()
    
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
    })

@login_required
def random_game(request):
    # Créer un jeu aléatoire avec des paramètres prédéfinis
    genre = Game.GENRE_CHOICES[0][0]  # Premier genre comme défaut
    ambiance = Game.AMBIANCE_CHOICES[0][0]  # Première ambiance comme défaut
    keywords = "adventure, mystery, magic"
    
    game_data = generate_game_content(genre, ambiance, keywords, "")
    
    if game_data:
        game = Game(
            owner=request.user,
            title=game_data.get('title', 'Random Game'),
            genre=genre,
            ambiance=ambiance,
            keywords=keywords,
            references="",
            universe_description=game_data.get('universe_description', ''),
            story_act1=game_data.get('story_act1', ''),
            story_act2=game_data.get('story_act2', ''),
            story_act3=game_data.get('story_act3', '')
        )
        game.save()
        
        # Création des personnages avec images générées
        characters = game_data.get('characters', [])
        for char_data in characters:
            character = Character(
                game=game,
                name=char_data.get('name', 'Random Character'),
                role=char_data.get('role', 'Unknown Role'),
                background=char_data.get('background', ''),
                abilities=char_data.get('abilities', '')
            )
            
            # Générer une image pour le personnage
            character_prompt = f"Portrait of {character.name}, a {character.role} from a {game.genre_name} game with {game.ambiance_name} ambiance."
            image_url = generate_image(character_prompt)
            if image_url:
                character.image = download_and_save_image(image_url, f"character_{character.name}.jpg", "characters")
            
            character.save()
        
        # Création des lieux avec images générées
        locations = game_data.get('locations', [])
        for loc_data in locations:
            location = Location(
                game=game,
                name=loc_data.get('name', 'Random Location'),
                description=loc_data.get('description', '')
            )
            
            # Générer une image pour le lieu
            location_prompt = f"{location.name} from a {game.genre_name} game with {game.ambiance_name} ambiance, {game.title}."
            image_url = generate_image(location_prompt)
            if image_url:
                location.image = download_and_save_image(image_url, f"location_{location.name}.jpg", "locations")
            
            location.save()
        
        messages.success(request, "Un jeu aléatoire a été généré avec succès!")
        return redirect('game_detail', game_id=game.id)
    else:
        messages.error(request, "Erreur lors de la génération du jeu aléatoire.")
        return redirect('dashboard')

def generate_game_content(genre, ambiance, keywords, references):
    """
    Fonction qui appelle l'API OpenAI (ChatGPT) pour générer le contenu du jeu
    """
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("Erreur: Clé API OpenAI non trouvée dans les variables d'environnement")
        return None
    
    # Initialiser le client OpenAI
    client = OpenAI(api_key=api_key)
    
    # Préparation du prompt pour l'API
    prompt = f"""
    Crée un concept de jeu vidéo original avec les paramètres suivants:
    - Genre: {genre}
    - Ambiance: {ambiance}
    - Mots-clés: {keywords}
    - Références (si spécifiées): {references}
    
    Renvoie uniquement un objet JSON avec le format suivant, sans explications ni guillemets supplémentaires:
    {{
      "title": "Titre du jeu",
      "universe_description": "Description détaillée de l'univers du jeu",
      "story_act1": "Description de l'acte 1 du scénario",
      "story_act2": "Description de l'acte 2 du scénario avec retournement",
      "story_act3": "Description de l'acte 3 et conclusion",
      "characters": [
        {{
          "name": "Nom du personnage 1",
          "role": "Rôle dans l'histoire",
          "background": "Histoire et motivations",
          "abilities": "Capacités et compétences"
        }},
        {{
          "name": "Nom du personnage 2",
          "role": "Rôle dans l'histoire",
          "background": "Histoire et motivations",
          "abilities": "Capacités et compétences"
        }}
      ],
      "locations": [
        {{
          "name": "Nom du lieu 1",
          "description": "Description immersive du lieu"
        }},
        {{
          "name": "Nom du lieu 2",
          "description": "Description immersive du lieu"
        }}
      ]
    }}
    """
    
    try:
        # Appel à l'API OpenAI
        response = client.chat.completions.create(
            model="gpt-4",  # Utilisation du modèle GPT-4 pour de meilleurs résultats
            messages=[
                {"role": "system", "content": "Tu es un concepteur de jeux vidéo professionnel spécialisé dans la création de concepts originaux."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extraction du contenu généré
        result_text = response.choices[0].message.content
        
        # Trouver le début et la fin du JSON dans la réponse
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = result_text[json_start:json_end]
            try:
                generated_data = json.loads(json_text)
                return generated_data
            except json.JSONDecodeError:
                print("Erreur: La réponse de l'API n'est pas au format JSON valide")
        else:
            print("Erreur: Impossible de trouver du JSON dans la réponse")
    
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API OpenAI: {e}")
    
    # En cas d'erreur, fournir des données par défaut
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
    Fonction qui utilise l'API DALL-E d'OpenAI pour générer une image
    """
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("Erreur: Clé API OpenAI non trouvée dans les variables d'environnement")
        return None
    
    client = OpenAI(api_key=api_key)
    
    try:
        response = client.images.generate(
            model="dall-e-3",  # Utilisation de la version 3 de DALL-E pour de meilleurs résultats
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        # Récupérer l'URL de l'image générée
        image_url = response.data[0].url
        return image_url
        
    except Exception as e:
        print(f"Erreur lors de la génération d'image: {e}")
        return None

def download_and_save_image(url, filename, subfolder):
    """
    Télécharge une image depuis une URL et la sauvegarde dans le système de fichiers
    Retourne le chemin relatif pour le champ ImageField
    """
    try:
        # Télécharger l'image
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            return None
        
        # Créer le dossier media s'il n'existe pas
        import os

        from django.conf import settings
        
        media_path = os.path.join(settings.MEDIA_ROOT, subfolder)
        if not os.path.exists(media_path):
            os.makedirs(media_path, exist_ok=True)
        
        # Nettoyer le nom du fichier pour éviter les problèmes de caractères spéciaux
        import re
        safe_filename = re.sub(r'[^\w\s.-]', '', filename)
        safe_filename = re.sub(r'\s+', '_', safe_filename)
        
        # Chemin complet du fichier
        file_path = os.path.join(media_path, safe_filename)
        
        # Enregistrer l'image
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Retourner le chemin relatif pour le modèle
        return f"{subfolder}/{safe_filename}"
        
    except Exception as e:
        print(f"Erreur lors du téléchargement de l'image: {e}")
        return None