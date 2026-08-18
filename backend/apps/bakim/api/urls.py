from django.urls import path

from apps.bakim.api import views

urlpatterns = [
    path("bakim/is-emirleri/", views.IsEmriListesi.as_view(), name="is-emri-listesi"),
    path(
        "bakim/is-emirleri/<uuid:pk>/",
        views.IsEmriDetayi.as_view(),
        name="is-emri-detayi",
    ),
    path(
        "bakim/is-emirleri/<uuid:pk>/ata/",
        views.IsEmriAtama.as_view(),
        name="is-emri-atama",
    ),
    path(
        "bakim/is-emirleri/<uuid:pk>/durum-gecisi/",
        views.IsEmriDurumGecisi.as_view(),
        name="is-emri-durum-gecisi",
    ),
    path(
        "bakim/is-emirleri/<uuid:pk>/oncelik-override/",
        views.IsEmriOncelikOverride.as_view(),
        name="is-emri-oncelik-override",
    ),
    path("makineler/", views.MakineListe.as_view(), name="makine-listesi"),
    path("makineler/<int:pk>/", views.MakineDetay.as_view(), name="makine-detayi"),
    path(
        "makineler/<int:pk>/aktiflik/",
        views.MakineAktiflik.as_view(),
        name="makine-aktiflik",
    ),
    path("parcalar/", views.ParcaListe.as_view(), name="parca-listesi"),
    path("parcalar/<int:pk>/", views.ParcaDetay.as_view(), name="parca-detayi"),
    path(
        "parcalar/<int:pk>/aktiflik/",
        views.ParcaAktiflik.as_view(),
        name="parca-aktiflik",
    ),
    path("stoklar/", views.StokListe.as_view(), name="stok-listesi"),
    path("stoklar/<int:pk>/", views.StokDetay.as_view(), name="stok-detayi"),
    path("ariza-parca-kurallari/", views.KuralListe.as_view(), name="kural-listesi"),
    path(
        "ariza-parca-kurallari/<int:pk>/",
        views.KuralDetay.as_view(),
        name="kural-detayi",
    ),
    path(
        "ariza-parca-kurallari/<int:pk>/aktiflik/",
        views.KuralAktiflik.as_view(),
        name="kural-aktiflik",
    ),
]
