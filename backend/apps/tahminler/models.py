import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.bakim.models import Makine, Parca


class ImmutableSnapshotQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValueError("Geçmiş tahmin snapshot'ı toplu olarak değiştirilemez.")

    def delete(self):
        raise ValueError("Geçmiş tahmin snapshot'ı toplu olarak silinemez.")


class ImmutableSnapshotModel(models.Model):
    objects = ImmutableSnapshotQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("Geçmiş tahmin snapshot'ı değiştirilemez.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Geçmiş tahmin snapshot'ı silinemez.")


class TahminKaydi(ImmutableSnapshotModel):
    class Kaynak(models.TextChoices):
        MANUEL = "MANUEL", "Manuel"
        REPLAY = "REPLAY", "Replay"
        ENTEGRASYON = "ENTEGRASYON", "Entegrasyon"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    makine = models.ForeignKey(
        Makine, on_delete=models.PROTECT, related_name="tahmin_kayitlari"
    )
    olusturan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tahmin_kayitlari",
    )
    trace_id = models.CharField(max_length=64)
    kaynak = models.CharField(max_length=12, choices=Kaynak.choices)
    olcum_zamani = models.DateTimeField()
    olusturulma_zamani = models.DateTimeField(auto_now_add=True)
    idempotency_key = models.CharField(max_length=128)
    payload_fingerprint = models.CharField(max_length=64)
    makine_kodu_snapshot = models.CharField(max_length=50)
    makine_adi_snapshot = models.CharField(max_length=150)
    kritiklik_snapshot = models.PositiveSmallIntegerField()
    sensor_snapshot = models.JSONField()
    risk_orani = models.FloatField()
    risk_uyarisi = models.BooleanField()
    binary_threshold = models.FloatField()
    binary_model_version = models.CharField(max_length=100)
    binary_pipeline_version = models.CharField(max_length=50)
    failure_type_durum = models.CharField(max_length=32)
    failure_type_model_version = models.CharField(max_length=100, null=True)
    failure_type_pipeline_version = models.CharField(max_length=50, null=True)
    belirsiz_fiziksel_tip = models.BooleanField()
    aciklanabilirlik_durum = models.CharField(max_length=32)
    binary_base_value = models.FloatField(null=True)

    class Meta:
        db_table = "tahmin_kayitlari"
        ordering = ("-olcum_zamani", "-olusturulma_zamani", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("makine", "kaynak", "idempotency_key"),
                name="tahmin_idempotency_benzersiz",
            ),
            models.CheckConstraint(
                condition=Q(risk_orani__gte=0, risk_orani__lte=1),
                name="tahmin_risk_0_1",
            ),
            models.CheckConstraint(
                condition=Q(binary_threshold__gte=0, binary_threshold__lte=1),
                name="tahmin_threshold_0_1",
            ),
            models.CheckConstraint(
                condition=Q(kritiklik_snapshot__gte=1, kritiklik_snapshot__lte=5),
                name="tahmin_kritiklik_1_5",
            ),
        ]

    def __str__(self):
        return f"{self.makine_kodu_snapshot} - {self.olcum_zamani.isoformat()}"


class ArizaTipiSnapshot(ImmutableSnapshotModel):
    class Kod(models.TextChoices):
        TWF = "TWF", "TWF"
        HDF = "HDF", "HDF"
        PWF = "PWF", "PWF"
        OSF = "OSF", "OSF"

    tahmin = models.ForeignKey(
        TahminKaydi, on_delete=models.CASCADE, related_name="ariza_tipleri"
    )
    kod = models.CharField(max_length=3, choices=Kod.choices)
    olasilik = models.FloatField()
    threshold = models.FloatField()
    esik_asildi = models.BooleanField()
    guven_durumu = models.CharField(max_length=32, null=True)
    operasyonel_kullanima_uygun = models.BooleanField()
    guvenilir_aday = models.BooleanField()
    siralama = models.PositiveSmallIntegerField(null=True)
    base_value = models.FloatField(null=True)

    class Meta:
        db_table = "tahmin_ariza_tipi_snapshotlari"
        ordering = ("siralama", "kod")
        constraints = [
            models.UniqueConstraint(
                fields=("tahmin", "kod"), name="tahmin_ariza_kodu_benzersiz"
            ),
            models.CheckConstraint(
                condition=Q(olasilik__gte=0, olasilik__lte=1), name="ariza_olasilik_0_1"
            ),
            models.CheckConstraint(
                condition=Q(threshold__gte=0, threshold__lte=1),
                name="ariza_threshold_0_1",
            ),
        ]


class ShapEtkisiSnapshot(ImmutableSnapshotModel):
    tahmin = models.ForeignKey(
        TahminKaydi, on_delete=models.CASCADE, related_name="shap_etkileri"
    )
    ariza_tipi = models.ForeignKey(
        ArizaTipiSnapshot,
        on_delete=models.CASCADE,
        null=True,
        related_name="shap_etkileri",
    )
    hedef = models.CharField(max_length=32)
    sira = models.PositiveSmallIntegerField()
    feature = models.CharField(max_length=100)
    gorunen_ad = models.CharField(max_length=150)
    original_feature_value = models.JSONField()
    model_feature_value = models.FloatField()
    birim = models.CharField(max_length=20, null=True)
    shap_value = models.FloatField()
    yon = models.CharField(max_length=20)

    class Meta:
        db_table = "tahmin_shap_snapshotlari"
        ordering = ("hedef", "sira")
        constraints = [
            models.UniqueConstraint(
                fields=("tahmin", "hedef", "sira"), name="tahmin_shap_sira_benzersiz"
            ),
            models.CheckConstraint(
                condition=Q(sira__gte=1), name="tahmin_shap_sira_pozitif"
            ),
        ]


class ErpSnapshot(ImmutableSnapshotModel):
    class StokDurumu(models.TextChoices):
        MEVCUT = "MEVCUT", "Mevcut"
        KAYIT_YOK = "KAYIT_YOK", "Kayıt yok"

    tahmin = models.ForeignKey(
        TahminKaydi, on_delete=models.CASCADE, related_name="erp_snapshotlari"
    )
    ariza_tipi = models.ForeignKey(
        ArizaTipiSnapshot, on_delete=models.CASCADE, related_name="erp_snapshotlari"
    )
    parca = models.ForeignKey(
        Parca, on_delete=models.PROTECT, related_name="tahmin_erp_snapshotlari"
    )
    parca_kodu_snapshot = models.CharField(max_length=50)
    parca_adi_snapshot = models.CharField(max_length=150)
    gerekli_miktar = models.PositiveIntegerField()
    stok_durumu = models.CharField(
        max_length=10, choices=StokDurumu.choices, default=StokDurumu.MEVCUT
    )
    toplam_stok = models.PositiveIntegerField(null=True)
    kullanilabilir_stok = models.PositiveIntegerField(null=True)
    minimum_stok = models.PositiveIntegerField(null=True)
    tedarik_gun = models.PositiveIntegerField(null=True)
    stok_yeterli = models.BooleanField()
    deneysel = models.BooleanField()
    onerilen_aksiyon_snapshot = models.TextField()

    class Meta:
        db_table = "tahmin_erp_snapshotlari"
        ordering = ("ariza_tipi__siralama", "parca_kodu_snapshot")
        constraints = [
            models.UniqueConstraint(
                fields=("tahmin", "ariza_tipi", "parca"),
                name="tahmin_erp_parca_benzersiz",
            ),
            models.CheckConstraint(
                condition=Q(gerekli_miktar__gt=0), name="tahmin_erp_miktar_pozitif"
            ),
            models.CheckConstraint(
                condition=Q(toplam_stok__isnull=True) | Q(toplam_stok__gte=0),
                name="tahmin_erp_toplam_negatif_degil",
            ),
            models.CheckConstraint(
                condition=Q(kullanilabilir_stok__isnull=True)
                | Q(kullanilabilir_stok__gte=0),
                name="tahmin_erp_kullanilabilir_negatif_degil",
            ),
            models.CheckConstraint(
                condition=Q(minimum_stok__isnull=True) | Q(minimum_stok__gte=0),
                name="tahmin_erp_minimum_negatif_degil",
            ),
            models.CheckConstraint(
                condition=Q(tedarik_gun__isnull=True) | Q(tedarik_gun__gte=0),
                name="tahmin_erp_tedarik_negatif_degil",
            ),
        ]
