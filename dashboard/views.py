"""Vues privées de gestion du catalogue."""
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_POST

from product.models import Category, Product, ProductMedia, ProductOffer, ProductOfferItem, Review
from .forms import CategoryForm, MediaFormSet, OfferFormSet, ProductForm, VariantFormSet
from .services import ensure_default_offer


def is_dashboard_admin(user):
    return bool(user and user.is_authenticated and user.is_active and user.is_superuser)


class AdminOnlyAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise ValidationError("Identifiants invalides ou accès non autorisé.", code="invalid_login")


class DashboardLoginView(LoginView):
    template_name = "dashboard/login.html"
    authentication_form = AdminOnlyAuthenticationForm
    redirect_authenticated_user = False
    next_page = reverse_lazy("dashboard:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.set_expiry(1800)
        return response


@method_decorator(user_passes_test(is_dashboard_admin, login_url="dashboard:login"), name="dispatch")
class DashboardLogoutView(LogoutView):
    next_page = reverse_lazy("dashboard:login")


def dashboard_admin_required(view_func):
    return user_passes_test(is_dashboard_admin, login_url="dashboard:login")(view_func)


@dashboard_admin_required
def home(request):
    context = {
        "product_count": Product.objects.count(),
        "active_product_count": Product.objects.filter(is_active=True).count(),
        "category_count": Category.objects.count(),
        "active_offer_count": ProductOffer.objects.filter(is_active=True).count(),
        "pending_reviews_count": Review.objects.filter(is_approved=False).count(),
        "recent_products": Product.objects.select_related("category").order_by("-updated_at")[:6],
        "admin_links": [
            ("Catégories", reverse("dashboard:categories"), "Organiser les rayons de la boutique"),
            ("Produits", reverse("dashboard:products"), "Créer et mettre à jour le catalogue"),
            ("Offres commerciales", reverse("dashboard:offers"), "Gérer les prix et niveaux d'offre"),
            ("Avis clients", reverse("admin:product_review_changelist"), "Modérer les avis avant publication"),
            ("Contenus avancés", reverse("admin:product_product_changelist"), "FAQ, médias et contenus détaillés"),
        ],
    }
    return render(request, "dashboard/home.html", context)


@dashboard_admin_required
def products(request):
    query = request.GET.get("q", "").strip()[:100]
    queryset = Product.objects.select_related("category").prefetch_related("variants", "offers", "media_items")
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(slug__icontains=query) | Q(category__name__icontains=query))
    return render(request, "dashboard/products.html", {"products": queryset.order_by("-updated_at"), "query": query})


@dashboard_admin_required
@require_http_methods(["GET", "POST"])
def product_edit(request, pk=None):
    instance = get_object_or_404(Product, pk=pk) if pk is not None else Product()
    is_new = instance.pk is None
    if request.method == "POST":
        form = ProductForm(request.POST, instance=instance)
        variants = VariantFormSet(request.POST, instance=instance, prefix="variants")
        media = MediaFormSet(request.POST, request.FILES, instance=instance, prefix="media")
        offers = OfferFormSet(request.POST, instance=instance, prefix="offers")
        if form.is_valid() and variants.is_valid() and media.is_valid() and offers.is_valid():
            with transaction.atomic():
                product = form.save()
                variants.instance = product
                media.instance = product
                offers.instance = product
                variants.save()
                primary_form = next((
                    item for item in media.forms
                    if item.cleaned_data and item.cleaned_data.get("is_primary") and not item.cleaned_data.get("DELETE")
                ), None)
                media.save()
                if primary_form and primary_form.instance.pk:
                    product.media_items.exclude(pk=primary_form.instance.pk).update(is_primary=False)
                    primary_form.instance.is_primary = True
                    primary_form.instance.save(update_fields=("is_primary",))
                else:
                    # Même si une requête modifiée coche plusieurs cases, une seule média reste principal.
                    primary = product.media_items.filter(is_primary=True).order_by("position", "pk").first()
                    if primary:
                        product.media_items.exclude(pk=primary.pk).update(is_primary=False)
                offers.save()
                for offer in product.offers.all():
                    ProductOfferItem.objects.get_or_create(
                        offer=offer, product=product, use_selected_variant=True,
                        defaults={"quantity": 1, "position": 0},
                    )
                ensure_default_offer(product)
            messages.success(request, "Produit créé avec ses offres et médias." if is_new else "Produit et offres mis à jour.")
            return redirect("dashboard:products")
    else:
        form = ProductForm(instance=instance)
        variants = VariantFormSet(instance=instance, prefix="variants")
        media = MediaFormSet(instance=instance, prefix="media")
        offers = OfferFormSet(instance=instance, prefix="offers")
    return render(request, "dashboard/product_form.html", {
        "form": form, "variants": variants, "media": media, "offers": offers,
        "product": instance, "is_new": is_new,
    })


@dashboard_admin_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    try:
        with transaction.atomic():
            product.delete()
    except ProtectedError:
        messages.error(request, f"« {name} » ne peut pas être supprimé : il est utilisé comme article complémentaire dans une autre offre. Modifiez d’abord cette composition.")
        return redirect("dashboard:products")
    messages.success(request, f"Le produit « {name} » et ses éléments associés ont été supprimés.")
    return redirect("dashboard:products")


@dashboard_admin_required
@require_http_methods(["GET", "POST"])
def categories(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Catégorie créée.")
            return redirect("dashboard:categories")
    else:
        form = CategoryForm()
    return render(request, "dashboard/categories.html", {
        "categories": Category.objects.annotate(product_count=models.Count("products")).order_by("position", "name"),
        "form": form,
    })


@dashboard_admin_required
@require_http_methods(["GET", "POST"])
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, request.FILES or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Catégorie mise à jour.")
        return redirect("dashboard:categories")
    return render(request, "dashboard/category_form.html", {"form": form, "category": category})


@dashboard_admin_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if category.products.exists():
        messages.error(request, f"Impossible de supprimer « {category.name} » : {category.products.count()} produit(s) y sont encore rattachés. Réaffectez-les ou supprimez-les d’abord.")
        return redirect("dashboard:categories")
    category.delete()
    messages.success(request, f"La catégorie « {category.name} » a été supprimée.")
    return redirect("dashboard:categories")


@dashboard_admin_required
def offers(request):
    product_filter = request.GET.get("product", "").strip()
    badge_filter = request.GET.get("badge", "").strip()
    state_filter = request.GET.get("state", "").strip()
    queryset = ProductOffer.objects.select_related("product").order_by("product__name", "position")
    if product_filter.isdigit():
        queryset = queryset.filter(product_id=int(product_filter))
    if badge_filter in dict(ProductOffer.BADGE_CHOICES):
        queryset = queryset.filter(badge=badge_filter)
    if state_filter in {"active", "inactive"}:
        queryset = queryset.filter(is_active=(state_filter == "active"))
    return render(request, "dashboard/offers.html", {
        "offers": queryset,
        "products_filter": Product.objects.order_by("name"),
        "selected_product": product_filter,
        "selected_badge": badge_filter,
        "selected_state": state_filter,
        "badge_choices": ProductOffer.BADGE_CHOICES,
    })
