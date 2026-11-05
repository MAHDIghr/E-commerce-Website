"""Formulaire de livraison : seules les données nécessaires sont collectées."""
from django import forms
from django.conf import settings
from config.commercial import (COUNTRY_CHOICES, shipping_countries, shipping_choices,
                               DESTINATION_UNAVAILABLE)

COUNTRIES = COUNTRY_CHOICES  # Pays de facturation ; la livraison utilise la liste approuvée.


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

    def __init__(self, *args, subtotal=None, offer_free=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["country"].choices = shipping_countries()
        self.fields["country"].error_messages["invalid_choice"] = DESTINATION_UNAVAILABLE
        choices = shipping_choices(subtotal, offer_free=offer_free)
        self.fields["shipping_method"].choices = [(method, label) for method, label, amount in choices]
        self.fields["shipping_method"].initial = choices[0][0]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("country") and cleaned.get("postal_code"):
            destination = ShippingQuoteForm(cleaned)
            if not destination.is_valid():
                for field, errors in destination.errors.items():
                    for error in errors:
                        self.add_error(field, error)
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


class ShippingQuoteForm(forms.Form):
    """Seules la destination et la forme du code postal sont nécessaires au devis."""
    country = forms.ChoiceField(label="Pays", choices=COUNTRIES)
    postal_code = forms.CharField(label="Code postal", max_length=20)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["country"].choices = shipping_countries()
        self.fields["country"].error_messages["invalid_choice"] = DESTINATION_UNAVAILABLE

    def clean(self):
        cleaned = super().clean()
        country = cleaned.get("country")
        postal = "".join(cleaned.get("postal_code", "").upper().split())
        prefixes = getattr(settings, "CHECKOUT_EXCLUDED_POSTAL_PREFIXES", {}).get(country, [])
        if postal and any(postal.startswith("".join(prefix.upper().split())) for prefix in prefixes):
            self.add_error("postal_code", DESTINATION_UNAVAILABLE)
        return cleaned
