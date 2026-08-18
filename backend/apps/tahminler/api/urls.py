from django.urls import path

from apps.tahminler.api.views import RiskTahmini

urlpatterns = [path("risk/", RiskTahmini.as_view(), name="risk-tahmini")]
