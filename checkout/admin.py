from django.contrib import admin
from .models import Order, OrderLine, PaymentAttempt, PromoCode, StripeWebhookEvent


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    can_delete = False
    readonly_fields = [field.name for field in OrderLine._meta.fields]
    fields = readonly_fields


class PaymentAttemptInline(admin.TabularInline):
    model = PaymentAttempt
    extra = 0
    can_delete = False
    readonly_fields = [field.name for field in PaymentAttempt._meta.fields]
    fields = readonly_fields


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("public_id", "email", "total", "currency", "status", "created_at")
    list_filter = ("status", "country", "shipping_method", "created_at")
    search_fields = ("public_id", "email", "full_name", "stripe_session_id", "stripe_payment_intent_id")
    readonly_fields = [field.name for field in Order._meta.fields]
    inlines = (OrderLineInline, PaymentAttemptInline)
    ordering = ("-created_at",)


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "processed_at")
    search_fields = ("event_id", "event_type")
    readonly_fields = ("event_id", "event_type", "processed_at")


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "minimum_subtotal", "maximum_discount", "is_active", "starts_at", "ends_at")
    list_filter = ("is_active", "discount_type", "once_per_email")
    search_fields = ("code",)
    list_editable = ("is_active",)
    ordering = ("code",)
