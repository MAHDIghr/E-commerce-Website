from django.urls import path

from . import views

app_name = "product"

urlpatterns = [
    path("", views.detail, {"slug": "sac-cabas-camel"}, name="index"),
    path("<slug:slug>/", views.detail, name="detail"),
]