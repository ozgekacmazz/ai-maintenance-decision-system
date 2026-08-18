import pytest
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.bakim.models import ArizaParcaKurali, Makine, Parca, Stok

pytestmark = pytest.mark.django_db


def makine_olustur(kod="M-001", kritiklik=3):
    return Makine.objects.create(
        makine_kodu=kod, ad="CNC Tezgâhı", tip="CNC", kritiklik=kritiklik
    )


def parca_olustur(kod="P-001"):
    return Parca.objects.create(parca_kodu=kod, ad="Rulman")


def test_gecerli_makine_saklanir():
    makine = makine_olustur()
    assert makine.kritiklik == 3


@pytest.mark.parametrize("kritiklik", [0, 6])
def test_gecersiz_kritiklik_database_tarafindan_reddedilir(kritiklik):
    with pytest.raises(IntegrityError), transaction.atomic():
        makine_olustur(kod=f"M-{kritiklik}", kritiklik=kritiklik)


def test_makine_kodu_tekrar_edemez():
    makine_olustur()
    with pytest.raises(IntegrityError), transaction.atomic():
        makine_olustur()


def test_parca_kodu_tekrar_edemez():
    parca_olustur()
    with pytest.raises(IntegrityError), transaction.atomic():
        parca_olustur()


def test_bir_parcaya_ikinci_stok_olusturulamaz():
    parca = parca_olustur()
    Stok.objects.create(parca=parca, adet=10)
    with pytest.raises(IntegrityError), transaction.atomic():
        Stok.objects.create(parca=parca, adet=20)


def test_negatif_adet_database_tarafindan_reddedilir():
    parca = parca_olustur()
    with pytest.raises(IntegrityError), transaction.atomic():
        Stok.objects.create(parca=parca, adet=-1)


def test_parca_silindiginde_stok_da_silinir():
    parca = parca_olustur()
    stok = Stok.objects.create(parca=parca, adet=10)
    stok_id = stok.pk
    parca.delete()
    assert not Stok.objects.filter(pk=stok_id).exists()


def test_gecerli_ariza_parca_kurali_olusturulur():
    kural = ArizaParcaKurali.objects.create(
        ariza_tipi=ArizaParcaKurali.ArizaTipi.TWF,
        parca=parca_olustur(),
        onerilen_aksiyon="Takımı inceleyin.",
    )
    assert kural.pk is not None


def test_ayni_ariza_parca_cifti_tekrar_edemez():
    parca = parca_olustur()
    alanlar = {
        "ariza_tipi": ArizaParcaKurali.ArizaTipi.HDF,
        "parca": parca,
        "onerilen_aksiyon": "Soğutmayı inceleyin.",
    }
    ArizaParcaKurali.objects.create(**alanlar)
    with pytest.raises(IntegrityError), transaction.atomic():
        ArizaParcaKurali.objects.create(**alanlar)


def test_parcasiz_rnf_genel_kurali_olusturulur():
    kural = ArizaParcaKurali.objects.create(
        ariza_tipi=ArizaParcaKurali.ArizaTipi.RNF,
        parca=None,
        onerilen_aksiyon="Genel teknik inceleme yapın.",
    )
    assert kural.parca is None


def test_ikinci_parcasiz_rnf_genel_kurali_reddedilir():
    alanlar = {
        "ariza_tipi": ArizaParcaKurali.ArizaTipi.RNF,
        "parca": None,
        "onerilen_aksiyon": "Genel teknik inceleme yapın.",
    }
    ArizaParcaKurali.objects.create(**alanlar)
    with pytest.raises(IntegrityError), transaction.atomic():
        ArizaParcaKurali.objects.create(**alanlar)


def test_kurala_bagli_parca_silinemez():
    parca = parca_olustur()
    ArizaParcaKurali.objects.create(
        ariza_tipi=ArizaParcaKurali.ArizaTipi.PWF,
        parca=parca,
        onerilen_aksiyon="Güç aktarımını inceleyin.",
    )
    with pytest.raises(ProtectedError):
        parca.delete()
