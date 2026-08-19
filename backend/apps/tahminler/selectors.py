from django.db.models import (
    Case,
    DateTimeField,
    Exists,
    F,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    When,
)

from apps.bakim.models import BakimIsEmri
from apps.tahminler.models import (
    ArizaTipiSnapshot,
    ErpSnapshot,
    ShapEtkisiSnapshot,
    TahminKaydi,
    TahminReddi,
)


def secilen_is_emri(tahmin):
    is_emirleri = getattr(tahmin, "tum_is_emirleri", ())
    return is_emirleri[0] if is_emirleri else None


def _sirali_is_emirleri():
    return BakimIsEmri.objects.select_related("olusturan").order_by(
        "-olusturulma_zamani", "-id"
    )


def tahmin_kaydi_listesi(*, filtreler):
    guvenilir = ArizaTipiSnapshot.objects.filter(guvenilir_aday=True).order_by(
        "siralama", "kod"
    )
    queryset = (
        TahminKaydi.objects.select_related("makine", "olusturan", "bakim_karari")
        .prefetch_related(
            Prefetch("ariza_tipleri", queryset=guvenilir, to_attr="guvenilir_tipler")
        )
        .annotate(
            erp_snapshot_var=Exists(
                ErpSnapshot.objects.filter(tahmin_id=OuterRef("pk"))
            )
        )
    )
    if "makine_id" in filtreler:
        queryset = queryset.filter(makine_id=filtreler["makine_id"])
    if "risk_uyarisi" in filtreler:
        queryset = queryset.filter(risk_uyarisi=filtreler["risk_uyarisi"])
    if "kaynak" in filtreler:
        queryset = queryset.filter(kaynak=filtreler["kaynak"])
    if "olcum_zamani_baslangic" in filtreler:
        queryset = queryset.filter(
            olcum_zamani__gte=filtreler["olcum_zamani_baslangic"]
        )
    if "olcum_zamani_bitis" in filtreler:
        queryset = queryset.filter(olcum_zamani__lte=filtreler["olcum_zamani_bitis"])
    if "ariza_tipi" in filtreler:
        queryset = queryset.filter(
            ariza_tipleri__kod=filtreler["ariza_tipi"],
            ariza_tipleri__guvenilir_aday=True,
        )
    if "genel_oncelik" in filtreler:
        queryset = queryset.filter(
            bakim_karari__genel_oncelik=filtreler["genel_oncelik"]
        )
    for field in ("oncelik_seviyesi", "ana_aksiyon", "karar_guveni"):
        if field in filtreler:
            queryset = queryset.filter(**{f"bakim_karari__{field}": filtreler[field]})
    if "minimum_nihai_skor" in filtreler:
        queryset = queryset.filter(
            bakim_karari__nihai_oncelik_skoru__gte=filtreler["minimum_nihai_skor"]
            - 1e-9
        )
    if "maksimum_nihai_skor" in filtreler:
        queryset = queryset.filter(
            bakim_karari__nihai_oncelik_skoru__lte=filtreler["maksimum_nihai_skor"]
            + 1e-9
        )
    ordering = {
        "nihai_oncelik": "bakim_karari__nihai_oncelik_skoru",
        "-nihai_oncelik": "-bakim_karari__nihai_oncelik_skoru",
        "olcum_zamani": "olcum_zamani",
        "-olcum_zamani": "-olcum_zamani",
        "risk_orani": "risk_orani",
        "-risk_orani": "-risk_orani",
        "makine_kritiklik": "kritiklik_snapshot",
        "-makine_kritiklik": "-kritiklik_snapshot",
    }
    if "sirala" in filtreler:
        if filtreler["sirala"] in {"genel_oncelik", "-genel_oncelik"}:
            priority = F("bakim_karari__genel_oncelik")
            priority_order = (
                priority.desc(nulls_last=True)
                if filtreler["sirala"].startswith("-")
                else priority.asc(nulls_last=True)
            )
            return queryset.distinct().order_by(
                priority_order,
                F("risk_orani").desc(),
                "olcum_zamani",
                "id",
            )
        return queryset.distinct().order_by(ordering[filtreler["sirala"]], "id")
    return queryset.distinct().order_by(
        F("bakim_karari__nihai_oncelik_skoru").desc(nulls_last=True),
        F("bakim_karari__teknik_aciliyet_skoru").desc(nulls_last=True),
        "olcum_zamani",
        "id",
    )


def tahmin_kaydi_detayi():
    erp = ErpSnapshot.objects.select_related("ariza_tipi")
    is_emirleri = _sirali_is_emirleri()
    return TahminKaydi.objects.select_related(
        "makine", "olusturan", "bakim_karari", "red_bilgisi", "red_bilgisi__reddeden"
    ).prefetch_related(
        Prefetch(
            "shap_etkileri",
            queryset=ShapEtkisiSnapshot.objects.order_by("hedef", "sira"),
            to_attr="tum_shap_etkileri",
        ),
        "ariza_tipleri",
        Prefetch("erp_snapshotlari", queryset=erp),
        "bakim_karari__gerekceler",
        "bakim_karari__destekleyici_aksiyonlar",
        "bakim_karari__uyarilar",
        Prefetch("is_emirleri", queryset=is_emirleri, to_attr="tum_is_emirleri"),
    )


def tahmin_loglari(*, filtreler):
    is_emri_var = BakimIsEmri.objects.filter(tahmin_kaydi_id=OuterRef("pk"))
    red_var = TahminReddi.objects.filter(tahmin_id=OuterRef("pk"))
    son_is_emri = _sirali_is_emirleri().filter(tahmin_kaydi_id=OuterRef("pk"))
    queryset = (
        TahminKaydi.objects.select_related(
            "makine",
            "bakim_karari",
            "red_bilgisi",
            "red_bilgisi__reddeden",
        )
        .annotate(
            log_is_emri_var=Exists(is_emri_var),
            log_red_var=Exists(red_var),
            log_onay_zamani=Subquery(
                son_is_emri.values("olusturulma_zamani")[:1],
                output_field=DateTimeField(),
            ),
            log_karar_zamani=Case(
                When(
                    Q(log_is_emri_var=True) & Q(log_red_var=False),
                    then=F("log_onay_zamani"),
                ),
                When(
                    Q(log_is_emri_var=False) & Q(log_red_var=True),
                    then=F("red_bilgisi__olusturulma_zamani"),
                ),
                default=None,
                output_field=DateTimeField(),
            ),
        )
        .prefetch_related(
            Prefetch(
                "is_emirleri",
                queryset=_sirali_is_emirleri(),
                to_attr="tum_is_emirleri",
            )
        )
    )

    if "karar_durumu" in filtreler:
        durumlar = {
            "BEKLIYOR": Q(log_is_emri_var=False, log_red_var=False),
            "ONAYLANDI": Q(log_is_emri_var=True, log_red_var=False),
            "REDDEDILDI": Q(log_is_emri_var=False, log_red_var=True),
            "TUTARSIZ": Q(log_is_emri_var=True, log_red_var=True),
        }
        queryset = queryset.filter(durumlar[filtreler["karar_durumu"]])
    if "makine_id" in filtreler:
        queryset = queryset.filter(makine_id=filtreler["makine_id"])
    if "makine_kodu" in filtreler:
        queryset = queryset.filter(makine_kodu_snapshot=filtreler["makine_kodu"])
    if "kaynak" in filtreler:
        queryset = queryset.filter(kaynak=filtreler["kaynak"])
    if "baslangic" in filtreler:
        queryset = queryset.filter(olcum_zamani__date__gte=filtreler["baslangic"])
    if "bitis" in filtreler:
        queryset = queryset.filter(olcum_zamani__date__lte=filtreler["bitis"])
    if "genel_oncelik" in filtreler:
        queryset = queryset.filter(
            bakim_karari__genel_oncelik=filtreler["genel_oncelik"]
        )

    sirala = filtreler.get("sirala", "-olcum_zamani")
    alan = sirala.removeprefix("-")
    descending = sirala.startswith("-")
    expressions = {
        "olcum_zamani": F("olcum_zamani"),
        "risk_orani": F("risk_orani"),
        "genel_oncelik": F("bakim_karari__genel_oncelik"),
        "karar_zamani": F("log_karar_zamani"),
    }
    expression = expressions[alan]
    return queryset.order_by(
        expression.desc(nulls_last=True)
        if descending
        else expression.asc(nulls_last=True),
        "id",
    )
