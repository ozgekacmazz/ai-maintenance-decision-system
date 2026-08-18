import pytest
from rest_framework.test import APIClient

from apps.bakim.models import ArizaParcaKurali, Makine, Parca, Stok
from apps.kullanicilar.models import Kullanici

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return Kullanici.objects.create_user(
        username="bakim-admin", rol="ADMIN", password="test-password"
    )


@pytest.fixture
def user():
    return Kullanici.objects.create_user(
        username="bakim-user", rol="USER", password="test-password"
    )


def istemci(kullanici=None):
    client = APIClient()
    if kullanici:
        client.force_authenticate(kullanici)
    return client


def hata_sozlesmesi(response, durum):
    assert response.status_code == durum
    assert set(response.data["hata"]) == {"kod", "mesaj", "alanlar", "trace_id"}
    assert response["X-Trace-ID"] == response.data["hata"]["trace_id"]


def test_anonim_401_user_yazma_403_ve_staff_rol_atlamaz(user):
    hata_sozlesmesi(istemci().get("/api/makineler/"), 401)
    hata_sozlesmesi(istemci(user).post("/api/makineler/", {}), 403)
    user.is_staff = True
    user.save()
    hata_sozlesmesi(istemci(user).post("/api/makineler/", {}), 403)


def test_makine_crud_gorunurluk_filtre_sayfalama_ve_cakisma(admin, user):
    client = istemci(admin)
    payload = {"kod": "  MK-1 ", "ad": "Pres", "tip": "Hidrolik", "kritiklik": 4}
    created = client.post("/api/makineler/", payload, format="json")
    assert created.status_code == 201 and created.data["kod"] == "MK-1"
    pk = created.data["id"]
    assert (
        client.patch(
            f"/api/makineler/{pk}/", {"ad": "Yeni Pres"}, format="json"
        ).status_code
        == 200
    )
    response = client.get("/api/makineler/?arama=Yeni&kritiklik=4&sirala=-kod")
    assert response.data["count"] == 1, response.data
    assert set(client.get("/api/makineler/?sayfa_boyutu=1").data) == {
        "count",
        "next",
        "previous",
        "results",
    }
    hata_sozlesmesi(client.get("/api/makineler/?sayfa_boyutu=101"), 400)
    hata_sozlesmesi(client.post("/api/makineler/", payload, format="json"), 409)
    hata_sozlesmesi(
        client.patch(f"/api/makineler/{pk}/", {"kritiklik": 6}, format="json"), 400
    )
    assert (
        client.post(
            f"/api/makineler/{pk}/aktiflik/", {"aktif": False}, format="json"
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/makineler/{pk}/aktiflik/", {"aktif": False}, format="json"
        ).status_code
        == 200
    )
    hata_sozlesmesi(istemci(user).get(f"/api/makineler/{pk}/"), 404)
    assert client.get(f"/api/makineler/{pk}/").status_code == 200


def test_parca_stok_crud_kurallar_ve_cakismalar(admin, user):
    client = istemci(admin)
    part = client.post(
        "/api/parcalar/",
        {"kod": " P-1 ", "ad": "Rulman", "aciklama": "x"},
        format="json",
    )
    assert part.status_code == 201
    pid = part.data["id"]
    stock_payload = {
        "parca_id": pid,
        "stok_adedi": 2,
        "tedarik_suresi_gun": 5,
        "kritik_stok_seviyesi": 3,
    }
    stock = client.post("/api/stoklar/", stock_payload, format="json")
    assert stock.status_code == 201
    assert (
        client.get("/api/stoklar/?dusuk_stok=true&sirala=stok_adedi").data["count"] == 1
    )
    assert (
        client.patch(
            f"/api/stoklar/{stock.data['id']}/", {"stok_adedi": 8}, format="json"
        ).data["stok_adedi"]
        == 8
    )
    hata_sozlesmesi(client.post("/api/stoklar/", stock_payload, format="json"), 409)
    hata_sozlesmesi(
        client.patch(
            f"/api/stoklar/{stock.data['id']}/", {"stok_adedi": -1}, format="json"
        ),
        400,
    )
    rule_payload = {
        "ariza_tipi": "TWF",
        "parca_id": pid,
        "onerilen_aksiyon": "Değiştir",
    }
    rule = client.post("/api/ariza-parca-kurallari/", rule_payload, format="json")
    assert rule.status_code == 201
    hata_sozlesmesi(
        client.post("/api/ariza-parca-kurallari/", rule_payload, format="json"), 409
    )
    assert (
        client.patch(
            f"/api/ariza-parca-kurallari/{rule.data['id']}/",
            {"onerilen_aksiyon": "Kontrol et"},
            format="json",
        ).status_code
        == 200
    )
    response = client.get("/api/ariza-parca-kurallari/?arama=Kontrol&ariza_tipi=TWF")
    assert response.data["count"] == 1, response.data
    assert (
        istemci(user).get("/api/parcalar/").data["results"][0]["stok"]["stok_adedi"]
        == 8
    )


def test_pasif_parca_stok_ve_aktif_kural_icin_reddedilir(admin):
    part = Parca.objects.create(parca_kodu="PASIF", ad="Pasif", aktif=False)
    client = istemci(admin)
    hata_sozlesmesi(
        client.post(
            "/api/stoklar/",
            {
                "parca_id": part.id,
                "stok_adedi": 0,
                "tedarik_suresi_gun": 0,
                "kritik_stok_seviyesi": 0,
            },
            format="json",
        ),
        400,
    )
    hata_sozlesmesi(
        client.post(
            "/api/ariza-parca-kurallari/",
            {"ariza_tipi": "HDF", "parca_id": part.id, "onerilen_aksiyon": "x"},
            format="json",
        ),
        400,
    )


def test_genel_kural_cakismasi_409(admin):
    client = istemci(admin)
    payload = {"ariza_tipi": "RNF", "parca_id": None, "onerilen_aksiyon": "İncele"}
    assert (
        client.post("/api/ariza-parca-kurallari/", payload, format="json").status_code
        == 201
    )
    hata_sozlesmesi(
        client.post("/api/ariza-parca-kurallari/", payload, format="json"), 409
    )


def test_user_yalniz_aktif_kayitlari_gorur_admin_hepsini_gorur(admin, user):
    Makine.objects.create(makine_kodu="A", ad="Aktif", tip="T", kritiklik=1)
    Makine.objects.create(
        makine_kodu="P", ad="Pasif", tip="T", kritiklik=1, aktif=False
    )
    response = istemci(user).get("/api/makineler/")
    assert response.data["count"] == 1, response.data
    assert istemci(admin).get("/api/makineler/").data["count"] == 2


def test_selectorlar_iliskileri_n_plus_one_olmadan_yukler(
    admin, django_assert_max_num_queries
):
    for index in range(5):
        part = Parca.objects.create(parca_kodu=f"Q{index}", ad="Parça")
        Stok.objects.create(parca=part, adet=index)
        ArizaParcaKurali.objects.create(
            ariza_tipi="TWF", parca=part, onerilen_aksiyon="x"
        )
    client = istemci(admin)
    with django_assert_max_num_queries(5):
        assert client.get("/api/parcalar/").status_code == 200
    with django_assert_max_num_queries(5):
        assert client.get("/api/ariza-parca-kurallari/").status_code == 200
