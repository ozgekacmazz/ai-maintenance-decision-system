from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

from apps.bakim.models import BakimIsEmri
from apps.bakim.work_order_policy import ACTIVE_STATES, TERMINAL_STATES


def is_emri_listesi(*, filtreler, now=None):
    now = now or timezone.now()
    queryset = BakimIsEmri.objects.select_related(
        "makine", "olusturan", "atanan_kullanici", "tahmin_kaydi"
    )
    mapping = {
        "durum": "durum",
        "etkin_oncelik_seviyesi": "etkin_oncelik_seviyesi",
        "kaynak_oncelik_seviyesi": "kaynak_oncelik_seviyesi",
        "makine_id": "makine_id",
        "atanan_kullanici_id": "atanan_kullanici_id",
        "olusturan_id": "olusturan_id",
        "manuel_oncelik_override": "manuel_oncelik_override",
        "ana_ariza_tipi": "kaynak_ana_ariza_tipi",
        "is_emri_numarasi": "is_emri_numarasi",
    }
    for key, field in mapping.items():
        if key in filtreler:
            queryset = queryset.filter(**{field: filtreler[key]})
    ranges = {
        "olusturulma_baslangic": "olusturulma_zamani__gte",
        "olusturulma_bitis": "olusturulma_zamani__lte",
        "hedef_mudahale_baslangic": "hedef_mudahale_zamani__gte",
        "hedef_mudahale_bitis": "hedef_mudahale_zamani__lte",
    }
    for key, lookup in ranges.items():
        if key in filtreler:
            queryset = queryset.filter(**{lookup: filtreler[key]})
    if "gecikmis" in filtreler:
        overdue = Q(durum__in=ACTIVE_STATES, hedef_mudahale_zamani__lt=now)
        queryset = queryset.filter(overdue if filtreler["gecikmis"] else ~overdue)
    priority_rank = Case(
        When(etkin_oncelik_seviyesi="KRITIK", then=Value(1)),
        When(etkin_oncelik_seviyesi="YUKSEK", then=Value(2)),
        When(etkin_oncelik_seviyesi="ORTA", then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )
    terminal_rank = Case(
        When(durum__in=TERMINAL_STATES, then=Value(1)),
        default=Value(0),
        output_field=IntegerField(),
    )
    overdue_rank = Case(
        When(durum__in=ACTIVE_STATES, hedef_mudahale_zamani__lt=now, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )
    queryset = queryset.annotate(
        oncelik_sirasi=priority_rank,
        terminal_sirasi=terminal_rank,
        gecikme_sirasi=overdue_rank,
    )
    ordering = {
        "etkin_oncelik": "oncelik_sirasi",
        "-etkin_oncelik": "-oncelik_sirasi",
        "hedef_mudahale_zamani": "hedef_mudahale_zamani",
        "-hedef_mudahale_zamani": "-hedef_mudahale_zamani",
        "olusturulma_zamani": "olusturulma_zamani",
        "-olusturulma_zamani": "-olusturulma_zamani",
        "guncellenme_zamani": "guncellenme_zamani",
        "-guncellenme_zamani": "-guncellenme_zamani",
        "makine_kritiklik": "tahmin_kaydi__kritiklik_snapshot",
        "-makine_kritiklik": "-tahmin_kaydi__kritiklik_snapshot",
        "kaynak_nihai_skor": "kaynak_nihai_oncelik_skoru",
        "-kaynak_nihai_skor": "-kaynak_nihai_oncelik_skoru",
        "durum": "durum",
        "-durum": "-durum",
    }
    if "sirala" in filtreler:
        return queryset.order_by(ordering[filtreler["sirala"]], "id")
    return queryset.order_by(
        "terminal_sirasi",
        "gecikme_sirasi",
        "oncelik_sirasi",
        "hedef_mudahale_zamani",
        "olusturulma_zamani",
        "id",
    )


def is_emri_detayi():
    return BakimIsEmri.objects.select_related(
        "makine",
        "olusturan",
        "atanan_kullanici",
        "tahmin_kaydi",
        "tahmin_kaydi__bakim_karari",
    ).prefetch_related("olaylar", "tahmin_kaydi__erp_snapshotlari")
