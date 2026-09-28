from django.shortcuts import render


def catalog(request):
    """Display the product catalog (front-end only for now).

    Products are rendered client-side from static/js/shop.js.
    They will be provided by a Product model in the back-end phase.
    """
    return render(request, "catalog.html")