from django import forms

from .models import Game, Location


class GameCreationForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['genre', 'ambiance', 'keywords', 'references']
        widgets = {
            'keywords': forms.TextInput(attrs={'placeholder': 'Séparés par des virgules'}),
            'references': forms.TextInput(attrs={'placeholder': 'Films, jeux, livres qui inspirent ce jeu'}),
        }


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }