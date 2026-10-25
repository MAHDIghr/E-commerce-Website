"""Formulaire de livraison : seules les données nécessaires sont collectées."""
import os
from decimal import Decimal
from django import forms

COUNTRIES = [
    ("FR", "France"), ("BE", "Belgique"), ("LU", "Luxembourg"),
    ("DE", "Allemagne"), ("ES", "Espagne"), ("IT", "Italie"),
    ("NL", "Pays-Bas"), ("PT", "Portugal"), ("CH", "Suisse"), ("GB", "Royaume-Uni"), ("CH", "Suisse"), ("GB", "Royaume-Uni"),
]


class CheckoutForm(forms.Form):
    full_name = forms.CharField(label="Nom complet", max_length=160, widget=forms.TextInput(attrs={"autocomplete": "name"}))
    email = forms.EmailField(label="Adresse e-mail", max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    phone = forms.CharField(label="Téléphone (facultatif)", max_length=40, required=False, widget=forms.TextInput(attrs={"autocomplete": "tel"}))
    address_line1 = forms.CharField(label="Adresse", max_length=180, widget=forms.TextInput(attrs={"autocomplete": "address-line1"}))
    address_line2 = forms.CharField(label="Complément d’adresse (facultatif)", max_length=180, required=False, widget=forms.TextInput(attrs={"autocomplete": "address-line2"}))
    postal_code = forms.CharField(label="Code postal", max_length=20, widget=forms.TextInput(attrs={"autocomplete": "postal-code"}))
    city = forms.CharField(label="Ville", max_length=100, widget=forms.TextInput(attrs={"autocomplete": "address-level2"}))
    country = forms.ChoiceField(label="Pays", choices=COUNTRIES, initial="FR", widget=forms.Select(attrs={"autocomplete": "country"}))
    shipping_method = forms.ChoiceField(label="Mode de livraison", choices=(), initial="standard")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        standard = Decimal(os.environ.get("CHECKOUT_STANDARD_SHIPPING", "4.90"))
        express = Decimal(os.environ.get("CHECKOUT_EXPRESS_SHIPPING", "9.90"))
        self.fields["shipping_method"].choices = (
            ("standard", f"Standard — {standard:.2f} €"),
            ("express", f"Express — {express:.2f} €"),
        )

    def clean_full_name(self):
        value = " ".join(self.cleaned_data["full_name"].split())
        if len(value) < 2:
            raise forms.ValidationError("Veuillez renseigner un nom complet.")
        return value
