"""Formulaire public de dépôt d'avis, soumis à modération."""
from django import forms
from django.core.exceptions import ValidationError


class ReviewForm(forms.Form):
    author_name = forms.CharField(
        label="Votre prénom ou nom affiché",
        min_length=2,
        max_length=100,
        strip=True,
        widget=forms.TextInput(attrs={"autocomplete": "name", "maxlength": "100", "placeholder": "Ex. : Camille"}),
    )
    rating = forms.ChoiceField(
        label="Votre note",
        choices=((1, "1 étoile"), (2, "2 étoiles"), (3, "3 étoiles"), (4, "4 étoiles"), (5, "5 étoiles")),
        coerce=int,
    )
    comment = forms.CharField(
        label="Votre avis", min_length=10, max_length=2000, strip=True,
        widget=forms.Textarea(attrs={"rows": 4, "maxlength": "2000", "placeholder": "Partagez votre expérience avec ce produit…"}),
    )
    # Champ piège pour les robots : il n'est jamais présenté aux visiteurs.
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_website(self):
        value = self.cleaned_data.get("website", "")
        if value:
            raise ValidationError("La soumission n'a pas pu être traitée.")
        return value
