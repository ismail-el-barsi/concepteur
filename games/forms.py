from django import forms

from .models import Game


class GameCreationForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['genre', 'ambiance', 'keywords', 'references']
        widgets = {
            'keywords': forms.TextInput(attrs={'placeholder': 'Ex: aventure, magie, trahison'}),
            'references': forms.TextInput(attrs={'placeholder': 'Ex: Zelda, Final Fantasy (optionnel)'}),
        }