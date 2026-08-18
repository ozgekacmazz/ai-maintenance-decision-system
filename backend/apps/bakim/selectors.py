from django.db.models import F, Q
from django.shortcuts import get_object_or_404

from apps.bakim.models import ArizaParcaKurali, Makine, Parca, Stok
from apps.kullanicilar.policies import aktif_admin_mi


def _gorunur(queryset, kullanici, alan="aktif"):
    return queryset if aktif_admin_mi(kullanici) else queryset.filter(**{alan: True})


def makineler(*, kullanici, filtreler):
    qs = _gorunur(Makine.objects.all(), kullanici)
    if arama := filtreler.get("arama"):
        qs = qs.filter(
            Q(makine_kodu__icontains=arama)
            | Q(ad__icontains=arama)
            | Q(tip__icontains=arama)
        )
    if "aktif" in filtreler:
        qs = qs.filter(aktif=filtreler["aktif"])
    if "kritiklik" in filtreler:
        qs = qs.filter(kritiklik=filtreler["kritiklik"])
    return qs.order_by(filtreler.get("sirala", "makine_kodu"), "id")


def makine_getir(*, kullanici, kayit_id):
    return get_object_or_404(_gorunur(Makine.objects.all(), kullanici), pk=kayit_id)


def parcalar(*, kullanici, filtreler):
    qs = _gorunur(Parca.objects.select_related("stok"), kullanici)
    if arama := filtreler.get("arama"):
        qs = qs.filter(Q(parca_kodu__icontains=arama) | Q(ad__icontains=arama))
    if "aktif" in filtreler:
        qs = qs.filter(aktif=filtreler["aktif"])
    return qs.order_by(filtreler.get("sirala", "parca_kodu"), "id")


def parca_getir(*, kullanici, kayit_id):
    return get_object_or_404(
        _gorunur(Parca.objects.select_related("stok"), kullanici), pk=kayit_id
    )


def stoklar(*, kullanici, filtreler):
    qs = Stok.objects.select_related("parca")
    if not aktif_admin_mi(kullanici):
        qs = qs.filter(parca__aktif=True)
    if arama := filtreler.get("arama"):
        qs = qs.filter(
            Q(parca__parca_kodu__icontains=arama) | Q(parca__ad__icontains=arama)
        )
    if filtreler.get("dusuk_stok") is True:
        qs = qs.filter(adet__lte=F("minimum_stok"))
    return qs.order_by(filtreler.get("sirala", "parca__parca_kodu"), "id")


def stok_getir(*, kullanici, kayit_id):
    qs = Stok.objects.select_related("parca")
    if not aktif_admin_mi(kullanici):
        qs = qs.filter(parca__aktif=True)
    return get_object_or_404(qs, pk=kayit_id)


def kurallar(*, kullanici, filtreler):
    qs = _gorunur(ArizaParcaKurali.objects.select_related("parca"), kullanici)
    if not aktif_admin_mi(kullanici):
        qs = qs.filter(Q(parca__isnull=True) | Q(parca__aktif=True))
    if arama := filtreler.get("arama"):
        qs = qs.filter(
            Q(ariza_tipi__icontains=arama)
            | Q(onerilen_aksiyon__icontains=arama)
            | Q(parca__parca_kodu__icontains=arama)
            | Q(parca__ad__icontains=arama)
        )
    for alan in ("ariza_tipi", "parca_id", "aktif"):
        if alan in filtreler:
            qs = qs.filter(**{alan: filtreler[alan]})
    return qs.order_by(filtreler.get("sirala", "ariza_tipi"), "id")


def kural_getir(*, kullanici, kayit_id):
    qs = _gorunur(ArizaParcaKurali.objects.select_related("parca"), kullanici)
    if not aktif_admin_mi(kullanici):
        qs = qs.filter(Q(parca__isnull=True) | Q(parca__aktif=True))
    return get_object_or_404(qs, pk=kayit_id)
