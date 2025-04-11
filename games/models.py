from django.contrib.auth.models import User
from django.db import models


class Game(models.Model):
    GENRE_CHOICES = [
        ('rpg', 'RPG'),
        ('fps', 'FPS'),
        ('adventure', 'Adventure'),
        ('strategy', 'Strategy'),
        ('puzzle', 'Puzzle'),
        ('platformer', 'Platformer'),
        ('metroidvania', 'Metroidvania'),
        ('visual_novel', 'Visual Novel'),
        ('other', 'Other'),
    ]
    
    AMBIANCE_CHOICES = [
        ('post_apocalyptic', 'Post-Apocalyptic'),
        ('fantasy', 'Fantasy'),
        ('cyberpunk', 'Cyberpunk'),
        ('scifi', 'Sci-Fi'),
        ('horror', 'Horror'),
        ('mystery', 'Mystery'),
        ('historical', 'Historical'),
        ('dreamlike', 'Dreamlike'),
        ('dark_fantasy', 'Dark Fantasy'),
        ('other', 'Other'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='games')
    title = models.CharField(max_length=100)
    genre = models.CharField(max_length=20, choices=GENRE_CHOICES)
    ambiance = models.CharField(max_length=20, choices=AMBIANCE_CHOICES)
    keywords = models.CharField(max_length=200)
    references = models.CharField(max_length=200, blank=True)
    
    universe_description = models.TextField()
    story_act1 = models.TextField()
    story_act2 = models.TextField()
    story_act3 = models.TextField()
    
    # Champs pour le système de narration dynamique
    has_dynamic_narrative = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def keyword_list(self):
        """Return keywords as a list of stripped strings"""
        if self.keywords:
            return [keyword.strip() for keyword in self.keywords.split(',')]
        return []
    
    @property
    def genre_name(self):
        """Return the display name for genre"""
        return self.get_genre_display()
        
    @property
    def ambiance_name(self):
        """Return the display name for ambiance"""
        return self.get_ambiance_display()


class Character(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='characters')
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    background = models.TextField()
    abilities = models.TextField()
    image = models.ImageField(upload_to='characters/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.game.title}"


class Location(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='locations/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.game.title}"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'game')
    
    def __str__(self):
        return f"{self.user.username} - {self.game.title}"


# Nouveau modèle pour les choix narratifs
class NarrativeChoice(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='narrative_choices')
    choice_text = models.CharField(max_length=200)
    outcome_description = models.TextField()
    act = models.IntegerField(choices=[(1, 'Acte 1'), (2, 'Acte 2'), (3, 'Acte 3')])
    
    def __str__(self):
        return f"{self.game.title} - Choix {self.id} (Acte {self.act})"


# Nouveau modèle pour l'historique narratif
class NarrativeHistory(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='narrative_history')
    choice_text = models.CharField(max_length=200)
    outcome_description = models.TextField()
    act = models.IntegerField(choices=[(1, 'Acte 1'), (2, 'Acte 2'), (3, 'Acte 3')])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name_plural = "Narrative histories"
    
    def __str__(self):
        return f"{self.game.title} - Acte {self.act} - {self.created_at.strftime('%d/%m/%Y')}"