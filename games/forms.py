from django import forms

from .models import Game, NarrativeChoice


class GameCreationForm(forms.ModelForm):
    has_dynamic_narrative = forms.BooleanField(
        required=False,
        label="Narration dynamique",
        help_text="Activer le système de narration dynamique avec des choix qui influencent l'histoire"
    )
    
    class Meta:
        model = Game
        fields = ['genre', 'ambiance', 'keywords', 'references', 'has_dynamic_narrative']
        widgets = {
            'keywords': forms.TextInput(attrs={'placeholder': 'Ex: aventure, magie, trahison'}),
            'references': forms.TextInput(attrs={'placeholder': 'Ex: Zelda, Final Fantasy (optionnel)'}),
        }


class NarrativeChoiceForm(forms.ModelForm):
    class Meta:
        model = NarrativeChoice
        fields = ['choice_text']
        widgets = {
            'choice_text': forms.TextInput(attrs={'placeholder': 'Décrivez votre choix narratif'}),
        }