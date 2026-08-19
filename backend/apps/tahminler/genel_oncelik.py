from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, InvalidOperation

GENEL_ONCELIK_FORMUL_SURUMU = "general-priority-1.0.0"

STOK_KATSAYISI_HASSASIYETI = Decimal("0.01")
HAM_GENEL_ONCELIK_HASSASIYETI = Decimal("0.0001")

_SIFIR = Decimal("0")
_BIR = Decimal("1")
_IKI = Decimal("2")
_BES = Decimal("5")
_YUZ = Decimal("100")


class GenelOncelikGirdiHatasi(ValueError):
    pass


@dataclass(frozen=True)
class GenelOncelikSonucu:
    risk_orani: Decimal
    makine_kritikligi: int
    tedarik_riski_skoru: Decimal
    stok_katsayisi: Decimal
    ham_genel_oncelik: Decimal
    genel_oncelik: int
    formul_surumu: str


def _decimal_deger(value, alan, *, minimum, maksimum):
    if value is None or isinstance(value, bool):
        raise GenelOncelikGirdiHatasi(
            f"{alan} sayısal ve {minimum} ile {maksimum} arasında olmalıdır."
        )
    try:
        sonuc = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise GenelOncelikGirdiHatasi(
            f"{alan} sayısal ve {minimum} ile {maksimum} arasında olmalıdır."
        ) from exc
    if not sonuc.is_finite():
        raise GenelOncelikGirdiHatasi(
            f"{alan} sonlu ve {minimum} ile {maksimum} arasında olmalıdır."
        )
    if sonuc < minimum or sonuc > maksimum:
        raise GenelOncelikGirdiHatasi(
            f"{alan} {minimum} ile {maksimum} arasında olmalıdır."
        )
    return sonuc


def _kritiklik_degeri(value):
    kritik = _decimal_deger(value, "makine_kritikligi", minimum=_BIR, maksimum=_BES)
    if kritik != kritik.to_integral_value():
        raise GenelOncelikGirdiHatasi(
            "makine_kritikligi 1 ile 5 arasında tam sayı olmalıdır."
        )
    return int(kritik)


def _oncelik_seviyesi(ham_deger):
    if ham_deger == _SIFIR:
        return 1
    seviye = int((ham_deger / _IKI).to_integral_value(rounding=ROUND_CEILING))
    return min(5, max(1, seviye))


def genel_oncelik_hesapla(*, risk_orani, makine_kritikligi, tedarik_riski_skoru):
    risk = _decimal_deger(risk_orani, "risk_orani", minimum=_SIFIR, maksimum=_BIR)
    kritiklik = _kritiklik_degeri(makine_kritikligi)
    tedarik = _decimal_deger(
        tedarik_riski_skoru,
        "tedarik_riski_skoru",
        minimum=_SIFIR,
        maksimum=_YUZ,
    )

    tam_stok_katsayisi = _BIR + (tedarik / _YUZ)
    tam_ham_oncelik = risk * Decimal(kritiklik) * tam_stok_katsayisi

    return GenelOncelikSonucu(
        risk_orani=risk,
        makine_kritikligi=kritiklik,
        tedarik_riski_skoru=tedarik,
        stok_katsayisi=tam_stok_katsayisi.quantize(
            STOK_KATSAYISI_HASSASIYETI, rounding=ROUND_HALF_UP
        ),
        ham_genel_oncelik=tam_ham_oncelik.quantize(
            HAM_GENEL_ONCELIK_HASSASIYETI, rounding=ROUND_HALF_UP
        ),
        genel_oncelik=_oncelik_seviyesi(tam_ham_oncelik),
        formul_surumu=GENEL_ONCELIK_FORMUL_SURUMU,
    )
