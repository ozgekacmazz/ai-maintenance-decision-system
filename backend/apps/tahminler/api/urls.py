from django.urls import path

from apps.tahminler.api.views import RiskTahmini, TahminKaydiDetayi, TahminKaydiListesi

urlpatterns = [
    path("risk/", RiskTahmini.as_view(), name="risk-tahmini"),
    path("kayitlar/", TahminKaydiListesi.as_view(), name="tahmin-kaydi-listesi"),
    path(
        "kayitlar/<uuid:pk>/", TahminKaydiDetayi.as_view(), name="tahmin-kaydi-detayi"
    ),
]
