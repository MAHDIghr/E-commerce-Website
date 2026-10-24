from django.contrib import admin
from django.utils.html import format_html

from .models import SignatureSelection


@admin.register(SignatureSelection)
class SignatureSelectionAdmin(admin.ModelAdmin):
    list_display = ("position", "product", "image_preview", "is_active")
    list_filter = ("is_active",)
    search_fields = ("product__name", "product__slug")
    autocomplete_fields = ("product",)
    list_editable = ("position", "is_active")
    list_select_related = ("product",)
    ordering = ("position", "pk")
    fields = ("product", "image", "alt_text", "position", "is_active", "image_preview")
    readonly_fields = ("image_preview",)
    list_per_page = 25

    @admin.display(description="Aperçu")
    def image_preview(self, obj):
        if not obj or not obj.image:
            return "Aucune image"
        return format_html(
            '<img src="{}" alt="" style="width:72px;height:88px;object-fit:contain;" loading="lazy">',
            obj.image.url,
        )
