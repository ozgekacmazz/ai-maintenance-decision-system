from django.db import IntegrityError, transaction

from apps.bakim.exceptions import BakimDogrulamaHatasi
from apps.bakim.models import ArizaParcaKurali, Makine, Parca, Stok
from apps.core.exceptions import KaynakCakismasiHatasi


def _kaydet(nesne):
    try:
        nesne.save()
    except IntegrityError as exc:
        raise KaynakCakismasiHatasi from exc
    return nesne


@transaction.atomic
def makine_olustur(*, veriler):
    return _kaydet(Makine(**veriler))


@transaction.atomic
def makine_guncelle(*, makine, veriler):
    for alan, deger in veriler.items():
        setattr(makine, alan, deger)
    return _kaydet(makine)


def makine_aktiflik_degistir(*, makine, aktif):
    return makine_guncelle(makine=makine, veriler={"aktif": aktif})


@transaction.atomic
def parca_olustur(*, veriler):
    return _kaydet(Parca(**veriler))


@transaction.atomic
def parca_guncelle(*, parca, veriler):
    for alan, deger in veriler.items():
        setattr(parca, alan, deger)
    return _kaydet(parca)


def parca_aktiflik_degistir(*, parca, aktif):
    return parca_guncelle(parca=parca, veriler={"aktif": aktif})


def _aktif_parca_dogrula(parca):
    if not parca.aktif:
        raise BakimDogrulamaHatasi({"parca_id": ["Pasif parça kullanılamaz."]})


@transaction.atomic
def stok_olustur(*, veriler):
    _aktif_parca_dogrula(veriler["parca"])
    return _kaydet(Stok(**veriler))


@transaction.atomic
def stok_guncelle(*, stok, veriler):
    kilitli = Stok.objects.select_for_update().get(pk=stok.pk)
    for alan, deger in veriler.items():
        setattr(kilitli, alan, deger)
    return _kaydet(kilitli)


def _aktif_kural_dogrula(*, aktif, parca):
    if aktif and parca is not None and not parca.aktif:
        raise BakimDogrulamaHatasi(
            {"parca_id": ["Aktif kural pasif parçaya bağlanamaz."]}
        )


@transaction.atomic
def kural_olustur(*, veriler):
    _aktif_kural_dogrula(aktif=veriler.get("aktif", True), parca=veriler.get("parca"))
    return _kaydet(ArizaParcaKurali(**veriler))


@transaction.atomic
def kural_guncelle(*, kural, veriler):
    aktif = veriler.get("aktif", kural.aktif)
    parca = veriler.get("parca", kural.parca)
    _aktif_kural_dogrula(aktif=aktif, parca=parca)
    for alan, deger in veriler.items():
        setattr(kural, alan, deger)
    return _kaydet(kural)


def kural_aktiflik_degistir(*, kural, aktif):
    return kural_guncelle(kural=kural, veriler={"aktif": aktif})
