import json
import os
from datetime import datetime
from io import BytesIO

import openai
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from openai import OpenAI
from xhtml2pdf import pisa

from .forms import GameCreationForm
from .models import (Character, Favorite, Game, Location, NarrativeChoice,
                     NarrativeHistory)


def home(request):
    return render(request, 'games/home.html')

@login_required
def dashboard(request):
    games = Game.objects.filter(owner=request.user)
    # Get games this user has favorited
    favorites = Favorite.objects.filter(user=request.user)
    favorited_games = [favorite.game for favorite in favorites]
    
    return render(request, 'games/dashboard.html', {
        'games': games,
        'favorited_games': favorited_games
    })

@login_required
def create_game(request):
    if request.method == 'POST':
        form = GameCreationForm(request.POST)
        if form.is_valid():
            # Créer le jeu sans sauvegarder
            game = form.save(commit=False)
            game.owner = request.user
            
            # Récupérer les informations du formulaire
            genre = form.cleaned_data['genre']
            ambiance = form.cleaned_data['ambiance']
            keywords = form.cleaned_data['keywords']
            references = form.cleaned_data.get('references', '')
            has_dynamic_narrative = form.cleaned_data.get('has_dynamic_narrative', False)
            
            # Génération du contenu avec l'API OpenAI (ChatGPT)
            game_data = generate_game_content(genre, ambiance, keywords, references)
            
            if game_data:
                # Mise à jour des champs du jeu
                game.title = game_data.get('title', 'Untitled Game')
                game.universe_description = game_data.get('universe_description', '')
                game.story_act1 = game_data.get('story_act1', '')
                game.story_act2 = game_data.get('story_act2', '')
                game.story_act3 = game_data.get('story_act3', '')
                game.has_dynamic_narrative = has_dynamic_narrative
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
        form = GameCreationForm()
    
    return render(request, 'games/create_game.html', {'form': form})

@login_required
def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id, owner=request.user)
    characters = Character.objects.filter(game=game)
    locations = Location.objects.filter(game=game)
    
    # Check if this game is favorited
    is_favorited = Favorite.objects.filter(user=request.user, game=game).exists()
    
    return render(request, 'games/game_detail.html', {
        'game': game,
        'characters': characters,
        'locations': locations,
        'is_favorited': is_favorited
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

@login_required
def toggle_favorite(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    
    # Check if the game is already favorited
    favorite = Favorite.objects.filter(user=request.user, game=game).first()
    
    if favorite:
        # If already favorited, remove the favorite
        favorite.delete()
        messages.success(request, f"'{game.title}' a été retiré de vos favoris.")
    else:
        # If not favorited, add it to favorites
        Favorite.objects.create(user=request.user, game=game)
        messages.success(request, f"'{game.title}' a été ajouté à vos favoris.")
    
    # Redirect back to the page the user was on
    next_url = request.GET.get('next', 'dashboard')
    
    # Check if we're redirecting to game_detail and include the game_id
    if next_url == 'game_detail':
        return redirect('game_detail', game_id=game_id)
    
    return redirect(next_url)

@login_required
def favorites(request):
    # Get all favorites for the current user
    favorites = Favorite.objects.filter(user=request.user)
    favorited_games = [favorite.game for favorite in favorites]
    
    return render(request, 'games/favorites.html', {'games': favorited_games})

# Ajouter cette fonction pour aider xhtml2pdf à trouver les fichiers statiques
def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those resources
    """
    # Utiliser Django's static finder pour trouver les fichiers
    if uri.startswith(settings.STATIC_URL):
        path = finders.find(uri.replace(settings.STATIC_URL, ""))
        return path
    
    # Gérer les fichiers média
    elif uri.startswith(settings.MEDIA_URL):
        return os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    
    # Gérer les urls absolues
    elif uri.startswith("http"):
        return uri
    
    # Gestion par défaut
    return uri

@login_required
def export_game_pdf(request, game_id):
    """
    Export a game as a styled PDF document using xhtml2pdf
    """
    game = get_object_or_404(Game, id=game_id, owner=request.user)
    characters = Character.objects.filter(game=game)
    locations = Location.objects.filter(game=game)
    
    keywords = game.keywords.split(',') if game.keywords else []
    keywords = [k.strip() for k in keywords]
    
    # Prepare the context for the template
    context = {
        'game': game,
        'characters': characters,
        'locations': locations,
        'keywords': keywords,
        'generation_date': datetime.now().strftime("%d/%m/%Y"),
        'STATIC_URL': settings.STATIC_URL,
        'base_url': request.build_absolute_uri('/').rstrip('/')
    }
    
    # Render the template
    template = get_template('games/game_pdf.html')
    html_string = template.render(context)
    
    # Create HTTP response with PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{game.title.replace(" ", "_")}_gameforge.pdf"'
    
    # Convert HTML to PDF and write to response
    pdf_status = html_to_pdf(html_string, response, link_callback)
    
    # Return the response
    if pdf_status:
        return response
    else:
        return HttpResponse("Une erreur s'est produite lors de la génération du PDF.", status=500)

def html_to_pdf(html_string, output, link_callback=None):
    """
    Simple function to convert HTML to PDF using xhtml2pdf
    """
    # Convert external URLs in the HTML string to base64 for images
    pisa_status = pisa.CreatePDF(
        src=html_string,
        dest=output,
        encoding='utf-8',
        link_callback=link_callback
    )
    
    # Return True if PDF generation was successful
    return pisa_status.err == 0

def generate_game_content(genre, ambiance, keywords, references):
    """
    Fonction qui appelle l'API OpenAI (ChatGPT) pour générer le contenu du jeu
    """
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not github_token:
        print("Erreur: Token GitHub non trouvé dans les variables d'environnement")
        return None
    
    # Initialiser le client OpenAI avec la nouvelle configuration
    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=github_token,
    )
    
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
        # Appel à l'API OpenAI avec le nouveau format
        response = client.chat.completions.create(
            model="gpt-4o-mini",  
            messages=[
                {"role": "system", "content": "Tu es un concepteur de jeux vidéo professionnel spécialisé dans la création de concepts originaux."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            top_p=1
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

@login_required
def narrative_choices(request, game_id):
    game = get_object_or_404(Game, id=game_id, owner=request.user)
    
    if not game.has_dynamic_narrative:
        messages.error(request, "Ce jeu n'utilise pas le système de narration dynamique.")
        return redirect('game_detail', game_id=game.id)
    
    # Déterminer l'acte actuel en fonction de l'historique des choix
    narrative_history = NarrativeHistory.objects.filter(game=game)
    
    if narrative_history.count() == 0:
        current_act = 1
        current_act_name = "Introduction"
    elif narrative_history.filter(act=1).exists() and not narrative_history.filter(act=2).exists():
        current_act = 2
        current_act_name = "Développement"
    elif narrative_history.filter(act=2).exists():
        current_act = 3
        current_act_name = "Conclusion"
    
    # Récupérer les choix narratifs disponibles pour l'acte actuel
    current_choices = NarrativeChoice.objects.filter(game=game, act=current_act)
    
    return render(request, 'games/narrative_choices.html', {
        'game': game,
        'current_act': current_act,
        'current_act_name': current_act_name,
        'current_choices': current_choices,
        'narrative_history': narrative_history
    })

@login_required
def generate_choices(request, game_id):
    if request.method != 'POST':
        return redirect('narrative_choices', game_id=game_id)
    
    game = get_object_or_404(Game, id=game_id, owner=request.user)
    
    if not game.has_dynamic_narrative:
        messages.error(request, "Ce jeu n'utilise pas le système de narration dynamique.")
        return redirect('game_detail', game_id=game.id)
    
    # Déterminer l'acte actuel
    narrative_history = NarrativeHistory.objects.filter(game=game)
    
    if narrative_history.count() == 0:
        current_act = 1
    elif narrative_history.filter(act=1).exists() and not narrative_history.filter(act=2).exists():
        current_act = 2
    elif narrative_history.filter(act=2).exists():
        current_act = 3
    
    # Générer de nouveaux choix narratifs avec l'IA
    choices = generate_narrative_choices(game, current_act, narrative_history)
    
    if choices:
        # Supprimer les anciens choix pour cet acte
        NarrativeChoice.objects.filter(game=game, act=current_act).delete()
        
        # Créer les nouveaux choix
        for choice_data in choices:
            NarrativeChoice.objects.create(
                game=game,
                act=current_act,
                choice_text=choice_data.get('choice_text', ''),
                outcome_description=choice_data.get('outcome_description', '')
            )
        
        messages.success(request, f"Nouveaux choix narratifs générés pour l'acte {current_act}.")
    else:
        messages.error(request, "Impossible de générer des choix narratifs pour le moment.")
    
    return redirect('narrative_choices', game_id=game.id)

@login_required
def select_choice(request, game_id, choice_id):
    if request.method != 'POST':
        return redirect('narrative_choices', game_id=game_id)
    
    game = get_object_or_404(Game, id=game_id, owner=request.user)
    choice = get_object_or_404(NarrativeChoice, id=choice_id, game=game)
    
    # Enregistrer ce choix dans l'historique
    NarrativeHistory.objects.create(
        game=game,
        act=choice.act,
        choice_text=choice.choice_text,
        outcome_description=choice.outcome_description
    )
    
    # Supprimer tous les choix de cet acte
    NarrativeChoice.objects.filter(game=game, act=choice.act).delete()
    
    # Mettre à jour l'histoire du jeu selon le choix
    update_game_story_with_choice(game, choice)
    
    messages.success(request, f"Votre choix a été enregistré et l'histoire a été mise à jour.")
    return redirect('narrative_choices', game_id=game.id)

def generate_narrative_choices(game, act, history):
    """
    Utilise l'API OpenAI pour générer des choix narratifs cohérents avec l'histoire du jeu
    """
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not github_token:
        return None
    
    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=github_token,
    )
    
    # Construire le contexte de l'histoire actuelle
    context = f"Titre: {game.title}\nGenre: {game.get_genre_display()}\nAmbiance: {game.get_ambiance_display()}\n\n"
    context += f"Description de l'univers: {game.universe_description}\n\n"
    
    if act == 1:
        context += f"Début de l'histoire: {game.story_act1}\n\n"
    elif act == 2:
        context += f"Début de l'histoire: {game.story_act1}\n\n"
        context += f"Développement: {game.story_act2}\n\n"
    elif act == 3:
        context += f"Début de l'histoire: {game.story_act1}\n\n"
        context += f"Développement: {game.story_act2}\n\n"
        context += f"Vers la conclusion: {game.story_act3}\n\n"
    
    # Ajouter l'historique des choix précédents
    if history.exists():
        context += "Historique des choix:\n"
        for entry in history:
            context += f"- Acte {entry.act}: {entry.choice_text} → {entry.outcome_description}\n"
    
    prompt = f"""
    {context}
    
    Générez 3 choix narratifs significatifs pour l'Acte {act} de cette histoire. Chaque choix doit être mémorable 
    et avoir un impact significatif sur l'histoire. Pour chaque choix, fournissez:
    1. Un texte de choix clair (ce que le joueur déciderait)
    2. Une description détaillée de l'impact de ce choix sur l'histoire
    
    Format attendu (JSON uniquement):
    [
        {{
            "choice_text": "Premier choix possible",
            "outcome_description": "Description de la conséquence du premier choix"
        }},
        {{
            "choice_text": "Second choix possible",
            "outcome_description": "Description de la conséquence du second choix"
        }},
        {{
            "choice_text": "Troisième choix possible",
            "outcome_description": "Description de la conséquence du troisième choix"
        }}
    ]
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Changed from gpt-4 to gpt-4o-mini
            messages=[
                {"role": "system", "content": "Tu es un concepteur narratif de jeux vidéo expert dans la création d'histoires interactives avec des choix significatifs."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            top_p=1
        )
        
        result_text = response.choices[0].message.content
        
        # Trouver le début et la fin du JSON dans la réponse
        json_start = result_text.find('[')
        json_end = result_text.rfind(']') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = result_text[json_start:json_end]
            try:
                choices_data = json.loads(json_text)
                return choices_data
            except json.JSONDecodeError:
                print("Erreur: La réponse de l'API n'est pas au format JSON valide")
        else:
            print("Erreur: Impossible de trouver du JSON dans la réponse")
    
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API OpenAI: {e}")
    
    return None

def update_game_story_with_choice(game, choice):
    """
    Met à jour l'histoire du jeu basée sur le choix narratif sélectionné
    """
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not github_token:
        return
    
    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=github_token,
    )
    
    # Construire le contexte de l'histoire actuelle
    context = f"Titre: {game.title}\nGenre: {game.get_genre_display()}\nAmbiance: {game.get_ambiance_display()}\n\n"
    context += f"Description de l'univers: {game.universe_description}\n\n"
    context += f"Histoire actuelle - Acte 1: {game.story_act1}\n\n"
    
    if choice.act >= 2:
        context += f"Histoire actuelle - Acte 2: {game.story_act2}\n\n"
    
    if choice.act >= 3:
        context += f"Histoire actuelle - Acte 3: {game.story_act3}\n\n"
    
    # Récupérer tous les choix précédents
    history = NarrativeHistory.objects.filter(game=game)
    
    if history.exists():
        context += "Historique des choix narratifs:\n"
        for entry in history:
            context += f"- Acte {entry.act}: {entry.choice_text} → {entry.outcome_description}\n"
    
    # Ajouter le choix actuel
    context += f"\nChoix actuel (Acte {choice.act}): {choice.choice_text}\n"
    context += f"Conséquence attendue: {choice.outcome_description}\n"
    
    # Demande à l'IA de mettre à jour la partie correspondante de l'histoire
    if choice.act == 1:
        prompt = f"""
        {context}
        
        Basé sur ce choix narratif important, réécris l'Acte 1 de l'histoire pour intégrer ce choix et ses conséquences.
        La nouvelle version doit être cohérente avec l'univers et le ton du jeu, tout en reflétant l'impact du choix.
        
        Renvoie uniquement le texte mis à jour pour l'Acte 1.
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  
                messages=[
                    {"role": "system", "content": "Tu es un écrivain narratif de jeux vidéo expert dans l'adaptation d'histoires selon les choix des joueurs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                top_p=1
            )
            
            updated_story = response.choices[0].message.content
            game.story_act1 = updated_story
            game.save()
            
        except Exception as e:
            print(f"Erreur lors de la mise à jour de l'histoire: {e}")
            
    elif choice.act == 2:
        prompt = f"""
        {context}
        
        Basé sur ce choix narratif important, réécris l'Acte 2 de l'histoire pour intégrer ce choix et ses conséquences.
        La nouvelle version doit être cohérente avec l'univers et le ton du jeu, tout en reflétant l'impact du choix.
        
        Renvoie uniquement le texte mis à jour pour l'Acte 2.
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  
                messages=[
                    {"role": "system", "content": "Tu es un écrivain narratif de jeux vidéo expert dans l'adaptation d'histoires selon les choix des joueurs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                top_p=1
            )
            
            updated_story = response.choices[0].message.content
            game.story_act2 = updated_story
            game.save()
            
        except Exception as e:
            print(f"Erreur lors de la mise à jour de l'histoire: {e}")
            
    elif choice.act == 3:
        prompt = f"""
        {context}
        
        Basé sur ce choix narratif important, réécris l'Acte 3 (conclusion) de l'histoire pour intégrer ce choix et ses conséquences.
        La nouvelle version doit être cohérente avec l'univers et le ton du jeu, tout en reflétant l'impact du choix.
        
        Renvoie uniquement le texte mis à jour pour l'Acte 3.
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[
                    {"role": "system", "content": "Tu es un écrivain narratif de jeux vidéo expert dans l'adaptation d'histoires selon les choix des joueurs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                top_p=1
            )
            
            updated_story = response.choices[0].message.content
            game.story_act3 = updated_story
            game.save()
            
        except Exception as e:
            print(f"Erreur lors de la mise à jour de l'histoire: {e}")
