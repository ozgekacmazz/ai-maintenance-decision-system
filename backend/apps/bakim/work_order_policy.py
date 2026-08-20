from copy import deepcopy
from datetime import timedelta

WORK_ORDER_POLICY_VERSION = "work-order-policy-1.0.0"
ACTIVE_STATES = frozenset({"ACIK", "ATANDI", "DEVAM_EDIYOR", "BEKLEMEDE"})
TERMINAL_STATES = frozenset({"TAMAMLANDI", "IPTAL_EDILDI"})
ALLOWED_TRANSITIONS = {
    "ACIK": frozenset({"ATANDI", "IPTAL_EDILDI"}),
    "ATANDI": frozenset({"DEVAM_EDIYOR", "BEKLEMEDE", "IPTAL_EDILDI"}),
    "DEVAM_EDIYOR": frozenset({"BEKLEMEDE", "TAMAMLANDI", "IPTAL_EDILDI"}),
    "BEKLEMEDE": frozenset({"ATANDI", "DEVAM_EDIYOR", "IPTAL_EDILDI"}),
    "TAMAMLANDI": frozenset(),
    "IPTAL_EDILDI": frozenset(),
}
SLA_HOURS = {"KRITIK": 4, "YUKSEK": 24, "ORTA": 72, "DUSUK": 168}
GENEL_ONCELIK_SLA_POLITIKASI_SURUMU = "general-priority-sla-1.0.0"
GENEL_ONCELIK_SLA_SAATLERI = {5: 4, 4: 24, 3: 72, 2: 120, 1: 168}


class IsEmriPolitikaHatasi(ValueError):
    pass


def gecisi_dogrula(*, mevcut_durum, hedef_durum, atanan_var, veriler):
    data = deepcopy(veriler)
    if hedef_durum == mevcut_durum or hedef_durum not in ALLOWED_TRANSITIONS.get(
        mevcut_durum, ()
    ):
        raise IsEmriPolitikaHatasi("İş emri durum geçişi geçersizdir.")
    if mevcut_durum in TERMINAL_STATES:
        raise IsEmriPolitikaHatasi("Terminal iş emri değiştirilemez.")
    if hedef_durum in {"ATANDI", "DEVAM_EDIYOR"} and not atanan_var:
        raise IsEmriPolitikaHatasi("Atanan kullanıcı gereklidir.")
    required = {
        "BEKLEMEDE": "bekleme_nedeni",
        "TAMAMLANDI": "tamamlama_notu",
        "IPTAL_EDILDI": "iptal_nedeni",
    }.get(hedef_durum)
    if required and not str(data.get(required) or "").strip():
        raise IsEmriPolitikaHatasi(f"{required} zorunludur.")
    return data


def hedef_mudahale_zamani(*, baslangic, oncelik):
    return baslangic + timedelta(hours=SLA_HOURS[oncelik])


def genel_oncelik_hedef_mudahale_zamani(*, baslangic, genel_oncelik):
    if (
        type(genel_oncelik) is not int
        or genel_oncelik not in GENEL_ONCELIK_SLA_SAATLERI
    ):
        raise IsEmriPolitikaHatasi(
            "genel_oncelik 1 ile 5 arasında bir tam sayı olmalıdır."
        )
    return baslangic + timedelta(hours=GENEL_ONCELIK_SLA_SAATLERI[genel_oncelik])


def gecikmis_mi(*, durum, hedef, simdi):
    return durum not in TERMINAL_STATES and simdi > hedef
