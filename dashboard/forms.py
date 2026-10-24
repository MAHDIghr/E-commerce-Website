"""Formulaires métier du dashboard privé."""
from django import forms
from django.forms import inlineformset_factory

from product.models import Category, Product, ProductMedia, ProductOffer, ProductVariant


class DashboardFormMixin:
    def apply_dashboard_classes(self):
        for field in self.fields.values():
            field.widget.attrs["class"] = (field.widget.attrs.get("class", "") + " field-control").strip()
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs["accept"] = "image/*"


class CategoryForm(DashboardFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug", "description", "image", "image_url", "alt_text", "is_active", "position")
        labels = {
            "position": "Ordre d'affichage des catégories",
            "image_url": "URL HTTPS de l'image (facultatif)",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_dashboard_classes()


class ProductForm(DashboardFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "name", "slug", "category", "short_description", "description",
            "brand_line", "tagline", "material", "is_new", "is_best_seller",
            "is_active", "published_at", "seo_title", "seo_description",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_dashboard_classes()
        self.fields["category"].queryset = Category.objects.order_by("position", "name")
        self.fields["published_at"].input_formats = ("%Y-%m-%dT%H:%M",)


VariantFormSet = inlineformset_factory(
    Product, ProductVariant,
    fields=("sku", "color_name", "color_slug", "color_code", "stock_quantity", "is_active", "position"),
    extra=0, min_num=1, validate_min=True, can_delete=True,
)
VariantFormSet.form.base_fields["sku"].label = "Référence interne de la variante"
VariantFormSet.form.base_fields["sku"].help_text = "Identifiant unique de cette déclinaison, par exemple SAC-CAMEL."
VariantFormSet.form.base_fields["position"].label = "Ordre d'affichage des couleurs"

MediaFormSet = inlineformset_factory(
    Product, ProductMedia,
    fields=("variant", "media_type", "image", "source_url", "poster_url", "alt_text", "is_primary", "position"),
    extra=0, can_delete=True,
)
MediaFormSet.form.base_fields["position"].label = "Ordre d'affichage des médias"
MediaFormSet.form.base_fields["source_url"].label = "URL HTTPS de l'image ou de la vidéo"
MediaFormSet.form.base_fields["poster_url"].label = "URL HTTPS de la vignette vidéo"

OfferFormSet = inlineformset_factory(
    Product, ProductOffer,
    fields=("badge", "display_delivery_label", "price", "is_featured", "is_active"),
    extra=0, min_num=1, validate_min=True, max_num=3, validate_max=True, can_delete=True,
)
