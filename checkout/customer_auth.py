"""Authentification client basée sur le système d'authentification Django."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

User = get_user_model()


class CustomerCreationForm(UserCreationForm):
    email = forms.EmailField(label="Adresse e-mail", max_length=254)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte utilisant cette adresse e-mail existe déjà.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user


class CustomerLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True
    next_page = reverse_lazy("checkout:customer_orders")


class CustomerLogoutView(LogoutView):
    next_page = reverse_lazy("home:home")


@require_http_methods(["GET", "POST"])
def customer_signup(request):
    if request.user.is_authenticated:
        return redirect("checkout:customer_orders")
    form = CustomerCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("checkout:customer_login")
    return render(request, "checkout/signup.html", {"form": form})
