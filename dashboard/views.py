"""Vues privées de gestion du catalogue."""
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods

from product.models import Category, Product, ProductOffer, Review
from .forms import CategoryForm, MediaFormSet, ProductForm, VariantFormSet


def is_dashboard_admin(user):
    """Le dashboard est réservé à un compte actif superutilisateur."""
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
        # Durée d'inactivité limitée ; Django renouvelle la session à la connexion.
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
            ("Catégories", reverse("admin:product_category_changelist"), "Organiser les rayons de la boutique"),
            ("Produits", reverse("dashboard:products"), "Créer et mettre à jour le catalogue"),
            ("Offres commerciales", reverse("admin:product_productoffer_changelist"), "Gérer les offres et leurs niveaux"),
            ("Avis clients", reverse("admin:product_review_changelist"), "Modérer les avis avant publication"),
            ("Contenus avancés", reverse("admin:product_product_changelist"), "FAQ, médias, variantes et contenus détaillés"),
        ],
    }
    return render(request, "dashboard/home.html", context)


@dashboard_admin_required
def products(request):
    query = request.GET.get("q", "").strip()[:100]
    queryset = Product.objects.select_related("category").prefetch_related("variants", "offers")
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(slug__icontains=query) | Q(category__name__icontains=query))
    return render(request, "dashboard/products.html", {
        "products": queryset.order_by("-updated_at"),
        "query": query,
    })


@dashboard_admin_required
@require_http_methods(["GET", "POST"])
def product_edit(request, pk=None):
    instance = get_object_or_404(Product, pk=pk) if pk is not None else Product()
    is_new = instance.pk is None

    if request.method == "POST":
        form = ProductForm(request.POST, instance=instance)
        variants = VariantFormSet(request.POST, instance=instance, prefix="variants")
        media = MediaFormSet(request.POST, request.FILES, instance=instance, prefix="media")
        if form.is_valid() and variants.is_valid() and media.is_valid():
            with transaction.atomic():
                product = form.save()
                variants.instance = product
                media.instance = product
                variants.save()
                media.save()
            messages.success(request, "Produit créé." if is_new else "Produit mis à jour.")
            return redirect("dashboard:products")
    else:
        form = ProductForm(instance=instance)
        variants = VariantFormSet(instance=instance, prefix="variants")
        media = MediaFormSet(instance=instance, prefix="media")

    return render(request, "dashboard/product_form.html", {
        "form": form, "variants": variants, "media": media,
        "product": instance, "is_new": is_new,
    })


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
        "categories": Category.objects.order_by("position", "name"),
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
def offers(request):
    return render(request, "dashboard/offers.html", {
        "offers": ProductOffer.objects.select_related("product").order_by("product__name", "position"),
    })


@dashboard_admin_required
def logout_redirect(request):
    # Ancien lien GET interdit : la déconnexion reste exclusivement en POST.
    raise PermissionDenied("Utilisez le formulaire de déconnexion sécurisé.")
