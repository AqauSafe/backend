from django.urls import path

from apps.sync.views import SyncBootstrapView, SyncImportView

app_name = "sync"

urlpatterns = [
    path("bootstrap/", SyncBootstrapView.as_view(), name="bootstrap"),
    path("import/", SyncImportView.as_view(), name="import"),
]
