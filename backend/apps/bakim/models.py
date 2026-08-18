import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import ImmutableSnapshotModel, ZamanDamgaliModel


class Makine(ZamanDamgaliModel):
    makine_kodu = models.CharField(
        max_length=50, unique=True, verbose_name="makine kodu"
    )
    ad = models.CharField(max_length=150, verbose_name="ad")
    tip = models.CharField(max_length=100, verbose_name="tip")
    kritiklik = models.PositiveSmallIntegerField(verbose_name="kritiklik")
    aktif = models.BooleanField(default=True, verbose_name="aktif")

    class Meta:
        db_table = "makineler"
        ordering = ("makine_kodu",)
        verbose_name = "makine"
        verbose_name_plural = "makineler"
        constraints = [
            models.CheckConstraint(
                condition=Q(kritiklik__gte=1, kritiklik__lte=5),
                name="makine_kritiklik_1_5",
            )
        ]

    def __str__(self):
        return f"{self.makine_kodu} - {self.ad}"


class Parca(ZamanDamgaliModel):
    parca_kodu = models.CharField(max_length=50, unique=True, verbose_name="parça kodu")
    ad = models.CharField(max_length=150, verbose_name="ad")
    aciklama = models.TextField(blank=True, verbose_name="açıklama")
    aktif = models.BooleanField(default=True, verbose_name="aktif")

    class Meta:
        db_table = "parcalar"
        ordering = ("parca_kodu",)
        verbose_name = "parça"
        verbose_name_plural = "parçalar"

    def __str__(self):
        return f"{self.parca_kodu} - {self.ad}"


class Stok(ZamanDamgaliModel):
    parca = models.OneToOneField(
        Parca,
        on_delete=models.CASCADE,
        related_name="stok",
        verbose_name="parça",
    )
    adet = models.PositiveIntegerField(default=0, verbose_name="adet")
    minimum_stok = models.PositiveIntegerField(default=0, verbose_name="minimum stok")
    tedarik_gun = models.PositiveIntegerField(default=0, verbose_name="tedarik günü")

    class Meta:
        db_table = "stoklar"
        verbose_name = "stok"
        verbose_name_plural = "stoklar"
        constraints = [
            models.CheckConstraint(
                condition=Q(adet__gte=0), name="stok_adet_negatif_degil"
            ),
            models.CheckConstraint(
                condition=Q(minimum_stok__gte=0), name="stok_minimum_negatif_degil"
            ),
            models.CheckConstraint(
                condition=Q(tedarik_gun__gte=0), name="stok_tedarik_gun_negatif_degil"
            ),
        ]

    def __str__(self):
        return f"{self.parca} - {self.adet} adet"


class ArizaParcaKurali(ZamanDamgaliModel):
    class ArizaTipi(models.TextChoices):
        TWF = "TWF", "Takım aşınması arızası"
        HDF = "HDF", "Isı dağılımı arızası"
        PWF = "PWF", "Güç arızası"
        OSF = "OSF", "Aşırı zorlanma arızası"
        RNF = "RNF", "Rastgele arıza"

    ariza_tipi = models.CharField(
        max_length=3, choices=ArizaTipi.choices, verbose_name="arıza tipi"
    )
    parca = models.ForeignKey(
        Parca,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ariza_kurallari",
        verbose_name="parça",
    )
    onerilen_aksiyon = models.TextField(verbose_name="önerilen aksiyon")
    aktif = models.BooleanField(default=True, verbose_name="aktif")
    gerekli_miktar = models.PositiveIntegerField(default=1)
    tercih_sirasi = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "ariza_parca_kurallari"
        verbose_name = "arıza-parça kuralı"
        verbose_name_plural = "arıza-parça kuralları"
        constraints = [
            models.UniqueConstraint(
                fields=("ariza_tipi", "parca"), name="ariza_parca_cifti_benzersiz"
            ),
            models.CheckConstraint(
                condition=Q(gerekli_miktar__gt=0), name="ariza_kural_miktar_pozitif"
            ),
            models.CheckConstraint(
                condition=Q(tercih_sirasi__gt=0), name="ariza_kural_sira_pozitif"
            ),
            models.UniqueConstraint(
                fields=("ariza_tipi",),
                condition=Q(parca__isnull=True),
                name="ariza_genel_kural_benzersiz",
            ),
        ]
        indexes = [
            models.Index(fields=("ariza_tipi", "aktif"), name="ariza_tipi_aktif_idx")
        ]

    def __str__(self):
        parca = self.parca.parca_kodu if self.parca else "genel"
        return f"{self.ariza_tipi} - {parca}"


class BakimIsEmri(models.Model):
    class Durum(models.TextChoices):
        ACIK = "ACIK", "Açık"
        ATANDI = "ATANDI", "Atandı"
        DEVAM_EDIYOR = "DEVAM_EDIYOR", "Devam ediyor"
        BEKLEMEDE = "BEKLEMEDE", "Beklemede"
        TAMAMLANDI = "TAMAMLANDI", "Tamamlandı"
        IPTAL_EDILDI = "IPTAL_EDILDI", "İptal edildi"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_emri_numarasi = models.CharField(max_length=32, unique=True, editable=False)
    tahmin_kaydi = models.ForeignKey(
        "tahminler.TahminKaydi", on_delete=models.PROTECT, related_name="is_emirleri"
    )
    makine = models.ForeignKey(
        Makine, on_delete=models.PROTECT, related_name="bakim_is_emirleri"
    )
    olusturan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="olusturdugu_is_emirleri",
    )
    atanan_kullanici = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name="atanan_is_emirleri",
    )
    durum = models.CharField(max_length=16, choices=Durum.choices, default=Durum.ACIK)
    baslik = models.CharField(max_length=200)
    aciklama = models.TextField(max_length=2000)
    idempotency_key = models.CharField(max_length=128)
    payload_fingerprint = models.CharField(max_length=64)
    politika_surumu = models.CharField(max_length=100)
    kaynak_motor_surumu = models.CharField(max_length=100)
    kaynak_teknik_aciliyet_skoru = models.FloatField()
    kaynak_tedarik_riski_skoru = models.FloatField()
    kaynak_nihai_oncelik_skoru = models.FloatField()
    kaynak_oncelik_seviyesi = models.CharField(max_length=10)
    kaynak_ana_aksiyon = models.CharField(max_length=32)
    kaynak_karar_guveni = models.CharField(max_length=10)
    kaynak_ana_ariza_tipi = models.CharField(max_length=3, null=True)
    etkin_oncelik_seviyesi = models.CharField(max_length=10)
    manuel_oncelik_override = models.BooleanField(default=False)
    override_nedeni = models.CharField(max_length=500, null=True)
    hedef_mudahale_zamani = models.DateTimeField()
    planlanan_baslangic_zamani = models.DateTimeField(null=True)
    gercek_baslangic_zamani = models.DateTimeField(null=True)
    tamamlanma_zamani = models.DateTimeField(null=True)
    iptal_zamani = models.DateTimeField(null=True)
    tamamlama_notu = models.TextField(max_length=2000, null=True)
    iptal_nedeni = models.CharField(max_length=500, null=True)
    bekleme_nedeni = models.CharField(max_length=500, null=True)
    version = models.PositiveIntegerField(default=1)
    olusturulma_zamani = models.DateTimeField(auto_now_add=True)
    guncellenme_zamani = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bakim_is_emirleri"
        constraints = [
            models.UniqueConstraint(
                fields=("olusturan", "idempotency_key"),
                name="is_emri_idempotency_benzersiz",
            ),
            models.UniqueConstraint(
                fields=("tahmin_kaydi",),
                condition=Q(durum__in=("ACIK", "ATANDI", "DEVAM_EDIYOR", "BEKLEMEDE")),
                name="tahmin_aktif_is_emri_benzersiz",
            ),
            models.CheckConstraint(
                condition=Q(version__gte=1), name="is_emri_version_pozitif"
            ),
            models.CheckConstraint(
                condition=Q(
                    durum__in=(
                        "ACIK",
                        "ATANDI",
                        "DEVAM_EDIYOR",
                        "BEKLEMEDE",
                        "TAMAMLANDI",
                        "IPTAL_EDILDI",
                    )
                ),
                name="is_emri_durum_gecerli",
            ),
            models.CheckConstraint(
                condition=Q(
                    kaynak_oncelik_seviyesi__in=("DUSUK", "ORTA", "YUKSEK", "KRITIK")
                ),
                name="is_emri_kaynak_oncelik_gecerli",
            ),
            models.CheckConstraint(
                condition=Q(
                    etkin_oncelik_seviyesi__in=("DUSUK", "ORTA", "YUKSEK", "KRITIK")
                ),
                name="is_emri_etkin_oncelik_gecerli",
            ),
        ]

    def __str__(self):
        return self.is_emri_numarasi


class IsEmriOlayi(ImmutableSnapshotModel):
    class OlayTipi(models.TextChoices):
        OLUSTURULDU = "OLUSTURULDU", "Oluşturuldu"
        ATANDI = "ATANDI", "Atandı"
        DURUM_DEGISTI = "DURUM_DEGISTI", "Durum değişti"
        BEKLEMEYE_ALINDI = "BEKLEMEYE_ALINDI", "Beklemeye alındı"
        DEVAM_ETTIRILDI = "DEVAM_ETTIRILDI", "Devam ettirildi"
        TAMAMLANDI = "TAMAMLANDI", "Tamamlandı"
        IPTAL_EDILDI = "IPTAL_EDILDI", "İptal edildi"
        ONCELIK_OVERRIDE_EDILDI = "ONCELIK_OVERRIDE_EDILDI", "Öncelik değiştirildi"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_emri = models.ForeignKey(
        BakimIsEmri, on_delete=models.CASCADE, related_name="olaylar"
    )
    olay_tipi = models.CharField(max_length=32, choices=OlayTipi.choices)
    onceki_durum = models.CharField(max_length=16, null=True)
    yeni_durum = models.CharField(max_length=16)
    gerceklestiren = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="is_emri_olaylari",
    )
    gerceklestiren_username_snapshot = models.CharField(max_length=150)
    trace_id = models.CharField(max_length=64)
    aciklama_snapshot = models.CharField(max_length=2000, null=True)
    onceki_atanan_username_snapshot = models.CharField(max_length=150, null=True)
    yeni_atanan_username_snapshot = models.CharField(max_length=150, null=True)
    onceki_oncelik = models.CharField(max_length=10, null=True)
    yeni_oncelik = models.CharField(max_length=10, null=True)
    version = models.PositiveIntegerField()
    olusturulma_zamani = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bakim_is_emri_olaylari"
        ordering = ("version", "olusturulma_zamani", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("is_emri", "version"), name="is_emri_olay_version_benzersiz"
            ),
            models.CheckConstraint(
                condition=Q(version__gte=1), name="is_emri_olay_version_pozitif"
            ),
        ]
