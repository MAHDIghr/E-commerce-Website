"""Site d'administration avec contrôle d'accès renforcé."""

from django.contrib.admin import AdminSite


class SuperuserAdminSite(AdminSite):
    site_header = "Administration My Line Collection"
    site_title = "Administration My Line Collection"
    index_title = "Gestion du catalogue"

    def has_permission(self, request):
        user = request.user
        return bool(user.is_authenticated and user.is_active and user.is_superuser)
