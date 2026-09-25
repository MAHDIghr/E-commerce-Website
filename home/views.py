from django.shortcuts import render


def home(request):
    """Display the home page."""
    return render(request, "home.html")