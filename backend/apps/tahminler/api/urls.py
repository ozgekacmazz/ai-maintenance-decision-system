from django.urls import path

from apps.tahminler.api import views
from apps.tahminler.api.views import RiskTahmini, TahminKaydiDetayi, TahminKaydiListesi

urlpatterns = [
    path("loglari/", views.TahminLoglari.as_view(), name="tahmin-loglari"),
    path(
        "replay-oturumlari/", views.ReplayOturumListesi.as_view(), name="replay-listesi"
    ),
    path(
        "replay-oturumlari/<uuid:pk>/",
        views.ReplayOturumDetayi.as_view(),
        name="replay-detayi",
    ),
    path(
        "replay-oturumlari/<uuid:pk>/ogeler/",
        views.ReplayOgeListesi.as_view(),
        name="replay-ogeleri",
    ),
    path(
        "replay-oturumlari/<uuid:pk>/baslat/",
        views.ReplayBaslat.as_view(),
        name="replay-baslat",
    ),
    path(
        "replay-oturumlari/<uuid:pk>/adim/",
        views.ReplayAdim.as_view(),
        name="replay-adim",
    ),
    path(
        "replay-oturumlari/<uuid:pk>/duraklat/",
        views.ReplayDuraklat.as_view(),
        name="replay-duraklat",
    ),
    path(
        "replay-oturumlari/<uuid:pk>/devam-et/",
        views.ReplayDevam.as_view(),
        name="replay-devam",
    ),
    path(
        "replay-oturumlari/<uuid:pk>/iptal/",
        views.ReplayIptal.as_view(),
        name="replay-iptal",
    ),
    path(
        "replay-oturumlari/<uuid:pk>/basarisizlari-yeniden-dene/",
        views.ReplayRetry.as_view(),
        name="replay-retry",
    ),
    path("risk/", RiskTahmini.as_view(), name="risk-tahmini"),
    path("input-domain/", views.InputDomainContract.as_view(), name="input-domain"),
    path("kayitlar/", TahminKaydiListesi.as_view(), name="tahmin-kaydi-listesi"),
    path(
        "kayitlar/<uuid:pk>/", TahminKaydiDetayi.as_view(), name="tahmin-kaydi-detayi"
    ),
    path(
        "kayitlar/<uuid:pk>/reddet/",
        views.TahminReddet.as_view(),
        name="tahmin-kaydi-reddet",
    ),
]
