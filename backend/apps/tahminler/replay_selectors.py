from django.db.models import Count, Prefetch, Q

from apps.tahminler.models import ReplayOgesi, ReplayOturumu


def _with_counts(queryset):
    return queryset.annotate(
        bekleyen_sayisi=Count("ogeler", filter=Q(ogeler__durum="BEKLIYOR")),
        isleniyor_sayisi=Count("ogeler", filter=Q(ogeler__durum="ISLENIYOR")),
        basarili_sayisi=Count("ogeler", filter=Q(ogeler__durum="BASARILI")),
        basarisiz_sayisi=Count("ogeler", filter=Q(ogeler__durum="BASARISIZ")),
        atlandi_sayisi=Count("ogeler", filter=Q(ogeler__durum="ATLANDI")),
    )


def replay_oturumlari(filters):
    queryset = _with_counts(ReplayOturumu.objects.select_related("olusturan", "makine"))
    for key, field in {
        "durum": "durum",
        "olusturan_id": "olusturan_id",
        "split": "split",
        "makine_id": "makine_id",
    }.items():
        if key in filters:
            queryset = queryset.filter(**{field: filters[key]})
    if "hatali_oge_var" in filters:
        condition = Q(basarisiz_sayisi__gt=0)
        queryset = queryset.filter(
            condition if filters["hatali_oge_var"] else ~condition
        )
    ordering = {
        "olusturulma_zamani": "olusturulma_zamani",
        "-olusturulma_zamani": "-olusturulma_zamani",
        "baslatilma_zamani": "baslatilma_zamani",
        "-baslatilma_zamani": "-baslatilma_zamani",
        "basarili_sayisi": "basarili_sayisi",
        "-basarili_sayisi": "-basarili_sayisi",
        "basarisiz_sayisi": "basarisiz_sayisi",
        "-basarisiz_sayisi": "-basarisiz_sayisi",
        "toplam_oge": "toplam_oge",
        "-toplam_oge": "-toplam_oge",
        "durum": "durum",
        "-durum": "-durum",
    }
    return queryset.order_by(
        ordering.get(filters.get("sirala"), "-son_islem_zamani"), "id"
    )


def replay_detayi():
    successful = (
        ReplayOgesi.objects.filter(durum="BASARILI")
        .select_related("tahmin_kaydi", "tahmin_kaydi__bakim_karari")
        .prefetch_related("tahmin_kaydi__ariza_tipleri")
    )
    return _with_counts(
        ReplayOturumu.objects.select_related("olusturan", "makine")
    ).prefetch_related("olaylar", Prefetch("ogeler", queryset=successful))


def replay_ogeleri(session_id, filters):
    queryset = ReplayOgesi.objects.filter(oturum_id=session_id).select_related(
        "tahmin_kaydi", "tahmin_kaydi__bakim_karari"
    )
    if "durum" in filters:
        queryset = queryset.filter(durum=filters["durum"])
    if "external_machine_id" in filters:
        queryset = queryset.filter(external_machine_id=filters["external_machine_id"])
    if "ground_truth_binary" in filters:
        queryset = queryset.filter(
            ground_truth_snapshot__makine_arizasi=int(filters["ground_truth_binary"])
        )
    if "sira_baslangic" in filters:
        queryset = queryset.filter(sira__gte=filters["sira_baslangic"])
    if "sira_bitis" in filters:
        queryset = queryset.filter(sira__lte=filters["sira_bitis"])
    return queryset.order_by("sira")
