from django.db.models import Exists, OuterRef, Prefetch

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
        TahminKaydi.objects.select_related("makine", "olusturan")
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
    return queryset.distinct()


def tahmin_kaydi_detayi():
    erp = ErpSnapshot.objects.select_related("ariza_tipi")
    root_shap = ShapEtkisiSnapshot.objects.filter(ariza_tipi__isnull=True)
    return TahminKaydi.objects.select_related("makine", "olusturan").prefetch_related(
        Prefetch("shap_etkileri", queryset=root_shap, to_attr="root_shap_etkileri"),
        "ariza_tipleri__shap_etkileri",
        Prefetch("erp_snapshotlari", queryset=erp),
    )
