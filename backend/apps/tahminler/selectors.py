from django.db.models import Exists, F, OuterRef, Prefetch

from apps.tahminler.models import (
    ArizaTipiSnapshot,
    ErpSnapshot,
    ShapEtkisiSnapshot,
    TahminKaydi,
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
        return queryset.distinct().order_by(ordering[filtreler["sirala"]], "id")
    return queryset.distinct().order_by(
        F("bakim_karari__nihai_oncelik_skoru").desc(nulls_last=True),
        F("bakim_karari__teknik_aciliyet_skoru").desc(nulls_last=True),
        "olcum_zamani",
        "id",
    )


def tahmin_kaydi_detayi():
    erp = ErpSnapshot.objects.select_related("ariza_tipi")
    return TahminKaydi.objects.select_related(
        "makine", "olusturan", "bakim_karari"
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
    )
