from django.urls import path

from apps.core.api.views import SaglikView

urlpatterns = [path("saglik/", SaglikView.as_view(), name="saglik")]
