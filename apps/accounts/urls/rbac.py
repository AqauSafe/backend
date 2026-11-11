from django.urls import path

from apps.accounts.views import PermissionListView, RoleListView

app_name = "rbac"

urlpatterns = [
    path("roles/", RoleListView.as_view(), name="roles"),
    path("permissions/", PermissionListView.as_view(), name="permissions"),
]
