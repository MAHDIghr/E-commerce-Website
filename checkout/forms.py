"""Formulaire de livraison : seules les données nécessaires sont collectées."""
from decimal import Decimal
from django import forms
from config.commercial import FREE_SHIPPING_THRESHOLD, SHIPPING_PRICES

COUNTRIES = [
    ("FR", "France"), ("BE", "Belgique"), ("LU", "Luxembourg"),
    ("DE", "Allemagne"), ("ES", "Espagne"), ("IT", "Italie"),
    ("NL", "Pays-Bas"), ("PT", "Portugal"), ("CH", "Suisse"), ("GB", "Royaume-Uni"),
]


class CheckoutForm(forms.Form):
    first_name = forms.CharField(label="Prénom", max_length=80, widget=forms.TextInput(attrs={"autocomplete": "given-name"}))
    last_name = forms.CharField(label="Nom", max_length=80, widget=forms.TextInput(attrs={"autocomplete": "family-name"}))
    email = forms.EmailField(label="Adresse e-mail", max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    phone = forms.CharField(label="Téléphone (facultatif, en cas de difficulté de livraison)", max_length=40, required=False, widget=forms.TextInput(attrs={"autocomplete": "tel"}))
    address_line1 = forms.CharField(label="Adresse (numéro et voie)", max_length=180, widget=forms.TextInput(attrs={"autocomplete": "shipping address-line1"}))
    postal_code = forms.CharField(label="Code postal", max_length=20, widget=forms.TextInput(attrs={"autocomplete": "shipping postal-code"}))
    city = forms.CharField(label="Ville", max_length=100, widget=forms.TextInput(attrs={"autocomplete": "shipping address-level2"}))
    country = forms.ChoiceField(label="Pays", choices=COUNTRIES, initial="FR", widget=forms.Select(attrs={"autocomplete": "shipping country"}))
    shipping_method = forms.ChoiceField(label="Mode de livraison", choices=(), initial="standard")
    billing_same_as_shipping = forms.BooleanField(label="Adresse de facturation identique à la livraison", required=False, initial=True)
    billing_address_line1 = forms.CharField(label="Adresse de facturation", max_length=180, required=False, widget=forms.TextInput(attrs={"autocomplete": "billing address-line1"}))
    billing_postal_code = forms.CharField(label="Code postal de facturation", max_length=20, required=False, widget=forms.TextInput(attrs={"autocomplete": "billing postal-code"}))
    billing_city = forms.CharField(label="Ville de facturation", max_length=100, required=False, widget=forms.TextInput(attrs={"autocomplete": "billing address-level2"}))
    billing_country = forms.ChoiceField(label="Pays de facturation", choices=COUNTRIES, required=False, widget=forms.Select(attrs={"autocomplete": "billing country"}))
    accept_terms = forms.BooleanField(label="J'accepte les conditions générales de vente", required=True)

    def __init__(self, *args, subtotal=None, **kwargs):
        super().__init__(*args, **kwargs)
        standard = SHIPPING_PRICES["standard"]
        express = SHIPPING_PRICES["express"]
        threshold = FREE_SHIPPING_THRESHOLD
        if subtotal is not None and Decimal(str(subtotal)) >= threshold:
            self.fields["shipping_method"].choices = (("free", "Livraison offerte — 0,00 €"),)
            self.fields["shipping_method"].initial = "free"
        else:
            self.fields["shipping_method"].choices = (
                ("standard", f"Standard — {standard:.2f} €"),
                ("express", f"Express — {express:.2f} €"),
            )
            self.fields["shipping_method"].initial = "standard"

    def clean(self):
        cleaned = super().clean()
        first = " ".join(cleaned.get("first_name", "").split())
        last = " ".join(cleaned.get("last_name", "").split())
        cleaned["full_name"] = f"{first} {last}".strip()
        if cleaned.get("billing_same_as_shipping"):
            for billing, shipping in (
                ("billing_address_line1", "address_line1"), ("billing_postal_code", "postal_code"),
                ("billing_city", "city"), ("billing_country", "country"),
            ):
                cleaned[billing] = cleaned.get(shipping, "")
        else:
            for field in ("billing_address_line1", "billing_postal_code", "billing_city", "billing_country"):
                if not cleaned.get(field):
                    self.add_error(field, "Ce champ est requis pour une adresse de facturation distincte.")
        return cleaned
