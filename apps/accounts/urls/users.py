from django.urls import path

from apps.accounts.views import MeView, UserListView

app_name = "users"

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("", UserListView.as_view(), name="list"),
]
