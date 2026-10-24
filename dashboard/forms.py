"""Formulaires simplifiés du dashboard, réutilisant les modèles métier existants."""
from django import forms
from django.forms import inlineformset_factory

from product.models import Category, Product, ProductMedia, ProductOffer, ProductVariant


class DashboardFormMixin:
    """Ajoute des classes CSS communes sans changer la validation métier."""

    def apply_dashboard_classes(self):
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = (existing + " field-control").strip()
            if isinstance(widget, forms.FileInput):
                widget.attrs["accept"] = "image/*"


class CategoryForm(DashboardFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug", "description", "image", "image_url", "alt_text", "is_active", "position")
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
    fields=("sku", "color_name", "color_slug", "color_code", "price", "compare_at_price", "stock_quantity", "is_active", "position"),
    extra=1, can_delete=True,
)
MediaFormSet = inlineformset_factory(
    Product, ProductMedia,
    fields=("media_type", "image", "source_url", "alt_text", "is_primary", "position"),
    extra=1, can_delete=True,
)


class OfferForm(DashboardFormMixin, forms.ModelForm):
    class Meta:
        model = ProductOffer
        fields = ("product", "badge", "display_delivery_label", "price", "is_featured", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_dashboard_classes()
        self.fields["product"].queryset = Product.objects.order_by("name")
