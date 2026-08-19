import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.bakim.models import Makine, Parca
from apps.core.models import ImmutableSnapshotModel


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
    input_domain_contract_surumu = models.CharField(
        max_length=100, null=True, blank=True
    )
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


class BakimKarariSnapshot(ImmutableSnapshotModel):
    class OncelikSeviyesi(models.TextChoices):
        DUSUK = "DUSUK", "Düşük"
        ORTA = "ORTA", "Orta"
        YUKSEK = "YUKSEK", "Yüksek"
        KRITIK = "KRITIK", "Kritik"

    class KararGuveni(models.TextChoices):
        YUKSEK = "YUKSEK", "Yüksek"
        ORTA = "ORTA", "Orta"
        DUSUK = "DUSUK", "Düşük"

    class Aksiyon(models.TextChoices):
        IZLEMEYE_DEVAM = "IZLEMEYE_DEVAM", "İzlemeye devam"
        PLANLI_KONTROL = "PLANLI_KONTROL", "Planlı kontrol"
        TEKNIK_INCELEME = "TEKNIK_INCELEME", "Teknik inceleme"
        ONCELIKLI_BAKIM_PLANLA = "ONCELIKLI_BAKIM_PLANLA", "Öncelikli bakım planla"
        ACIL_TEKNIK_DEGERLENDIRME = (
            "ACIL_TEKNIK_DEGERLENDIRME",
            "Acil teknik değerlendirme",
        )
        STOK_VERISINI_DOGRULA = "STOK_VERISINI_DOGRULA", "Stok verisini doğrula"
        TEDARIK_SURECINI_BASLAT = (
            "TEDARIK_SURECINI_BASLAT",
            "Tedarik sürecini başlat",
        )

    tahmin = models.OneToOneField(
        TahminKaydi, on_delete=models.CASCADE, related_name="bakim_karari"
    )
    motor_surumu = models.CharField(max_length=100)
    teknik_aciliyet_skoru = models.FloatField()
    tedarik_riski_skoru = models.FloatField()
    nihai_oncelik_skoru = models.FloatField()
    oncelik_seviyesi = models.CharField(max_length=10, choices=OncelikSeviyesi.choices)
    genel_oncelik = models.PositiveSmallIntegerField(null=True, blank=True)
    stok_katsayisi = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )
    ham_genel_oncelik = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True
    )
    genel_oncelik_formul_surumu = models.CharField(
        max_length=100, null=True, blank=True
    )
    ana_aksiyon = models.CharField(max_length=32, choices=Aksiyon.choices)
    ana_ariza_tipi = models.CharField(
        max_length=3, choices=ArizaTipiSnapshot.Kod.choices, null=True
    )
    karar_guveni = models.CharField(max_length=10, choices=KararGuveni.choices)
    olusturulma_zamani = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bakim_karari_snapshotlari"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    teknik_aciliyet_skoru__gte=0, teknik_aciliyet_skoru__lte=100
                ),
                name="karar_teknik_skor_0_100",
            ),
            models.CheckConstraint(
                condition=Q(tedarik_riski_skoru__gte=0, tedarik_riski_skoru__lte=100),
                name="karar_tedarik_skor_0_100",
            ),
            models.CheckConstraint(
                condition=Q(nihai_oncelik_skoru__gte=0, nihai_oncelik_skoru__lte=100),
                name="karar_nihai_skor_0_100",
            ),
            models.CheckConstraint(
                condition=Q(genel_oncelik__isnull=True)
                | Q(genel_oncelik__gte=1, genel_oncelik__lte=5),
                name="karar_genel_oncelik_1_5",
            ),
            models.CheckConstraint(
                condition=Q(stok_katsayisi__isnull=True)
                | Q(stok_katsayisi__gte=1, stok_katsayisi__lte=2),
                name="karar_stok_katsayisi_1_2",
            ),
            models.CheckConstraint(
                condition=Q(ham_genel_oncelik__isnull=True)
                | Q(ham_genel_oncelik__gte=0, ham_genel_oncelik__lte=10),
                name="karar_ham_genel_oncelik_0_10",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        genel_oncelik__isnull=True,
                        stok_katsayisi__isnull=True,
                        ham_genel_oncelik__isnull=True,
                        genel_oncelik_formul_surumu__isnull=True,
                    )
                    | Q(
                        genel_oncelik__isnull=False,
                        stok_katsayisi__isnull=False,
                        ham_genel_oncelik__isnull=False,
                        genel_oncelik_formul_surumu__isnull=False,
                    )
                ),
                name="karar_canonical_alanlar_birlikte",
            ),
            models.CheckConstraint(
                condition=Q(genel_oncelik_formul_surumu__isnull=True)
                | ~Q(genel_oncelik_formul_surumu=""),
                name="karar_formul_surumu_bos_degil",
            ),
            models.CheckConstraint(
                condition=Q(ana_ariza_tipi__isnull=True)
                | Q(ana_ariza_tipi__in=("HDF", "PWF", "OSF")),
                name="karar_ana_ariza_guvenilir",
            ),
            models.CheckConstraint(
                condition=Q(oncelik_seviyesi__in=("DUSUK", "ORTA", "YUKSEK", "KRITIK")),
                name="karar_oncelik_gecerli",
            ),
            models.CheckConstraint(
                condition=Q(
                    ana_aksiyon__in=(
                        "IZLEMEYE_DEVAM",
                        "PLANLI_KONTROL",
                        "TEKNIK_INCELEME",
                        "ONCELIKLI_BAKIM_PLANLA",
                        "ACIL_TEKNIK_DEGERLENDIRME",
                        "STOK_VERISINI_DOGRULA",
                        "TEDARIK_SURECINI_BASLAT",
                    )
                ),
                name="karar_ana_aksiyon_gecerli",
            ),
            models.CheckConstraint(
                condition=Q(karar_guveni__in=("YUKSEK", "ORTA", "DUSUK")),
                name="karar_guveni_gecerli",
            ),
        ]


class KararGerekcesiSnapshot(ImmutableSnapshotModel):
    class Etki(models.TextChoices):
        ARTIRDI = "ARTIRDI", "Artırdı"
        AZALTTI = "AZALTTI", "Azalttı"
        NOTR = "NOTR", "Nötr"

    karar = models.ForeignKey(
        BakimKarariSnapshot, on_delete=models.CASCADE, related_name="gerekceler"
    )
    kod = models.CharField(max_length=50)
    mesaj_snapshot = models.CharField(max_length=300)
    etki = models.CharField(max_length=10, choices=Etki.choices)
    puan_etkisi = models.FloatField(null=True)
    sira = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "karar_gerekcesi_snapshotlari"
        ordering = ("sira", "kod")
        constraints = [
            models.UniqueConstraint(
                fields=("karar", "sira"), name="karar_gerekce_sira_benzersiz"
            ),
            models.UniqueConstraint(
                fields=("karar", "kod"), name="karar_gerekce_kod_benzersiz"
            ),
            models.CheckConstraint(
                condition=Q(sira__gte=1), name="karar_gerekce_sira_pozitif"
            ),
            models.CheckConstraint(
                condition=Q(etki__in=("ARTIRDI", "AZALTTI", "NOTR")),
                name="karar_gerekce_etki_gecerli",
            ),
        ]


class KararAksiyonuSnapshot(ImmutableSnapshotModel):
    karar = models.ForeignKey(
        BakimKarariSnapshot,
        on_delete=models.CASCADE,
        related_name="destekleyici_aksiyonlar",
    )
    aksiyon = models.CharField(
        max_length=32, choices=BakimKarariSnapshot.Aksiyon.choices
    )
    sira = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "karar_aksiyonu_snapshotlari"
        ordering = ("sira", "aksiyon")
        constraints = [
            models.UniqueConstraint(
                fields=("karar", "sira"), name="karar_aksiyon_sira_benzersiz"
            ),
            models.UniqueConstraint(
                fields=("karar", "aksiyon"), name="karar_aksiyon_kod_benzersiz"
            ),
            models.CheckConstraint(
                condition=Q(sira__gte=1), name="karar_aksiyon_sira_pozitif"
            ),
            models.CheckConstraint(
                condition=Q(
                    aksiyon__in=(
                        "IZLEMEYE_DEVAM",
                        "PLANLI_KONTROL",
                        "TEKNIK_INCELEME",
                        "ONCELIKLI_BAKIM_PLANLA",
                        "ACIL_TEKNIK_DEGERLENDIRME",
                        "STOK_VERISINI_DOGRULA",
                        "TEDARIK_SURECINI_BASLAT",
                    )
                ),
                name="karar_destek_aksiyon_gecerli",
            ),
        ]


class KararUyarisiSnapshot(ImmutableSnapshotModel):
    karar = models.ForeignKey(
        BakimKarariSnapshot, on_delete=models.CASCADE, related_name="uyarilar"
    )
    kod = models.CharField(max_length=50)
    mesaj_snapshot = models.CharField(max_length=300)
    sira = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "karar_uyarisi_snapshotlari"
        ordering = ("sira", "kod")
        constraints = [
            models.UniqueConstraint(
                fields=("karar", "sira"), name="karar_uyari_sira_benzersiz"
            ),
            models.UniqueConstraint(
                fields=("karar", "kod"), name="karar_uyari_kod_benzersiz"
            ),
            models.CheckConstraint(
                condition=Q(sira__gte=1), name="karar_uyari_sira_pozitif"
            ),
        ]


class ReplayOturumu(models.Model):
    class Durum(models.TextChoices):
        HAZIR = "HAZIR", "Hazır"
        CALISIYOR = "CALISIYOR", "Çalışıyor"
        DURAKLATILDI = "DURAKLATILDI", "Duraklatıldı"
        TAMAMLANDI = "TAMAMLANDI", "Tamamlandı"
        IPTAL_EDILDI = "IPTAL_EDILDI", "İptal edildi"
        HATALI = "HATALI", "Hatalı"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    replay_numarasi = models.CharField(max_length=32, unique=True, editable=False)
    olusturan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="replay_oturumlari",
    )
    makine = models.ForeignKey(
        Makine, on_delete=models.PROTECT, related_name="replay_oturumlari"
    )
    durum = models.CharField(max_length=16, choices=Durum.choices, default=Durum.HAZIR)
    version = models.PositiveIntegerField(default=1)
    politika_surumu = models.CharField(max_length=100)
    kaynak_veri_seti = models.CharField(max_length=100)
    prepared_sha256 = models.CharField(max_length=64)
    split = models.CharField(max_length=12)
    baslangic_ofseti = models.PositiveIntegerField(default=0)
    toplam_oge = models.PositiveIntegerField()
    varsayilan_batch_boyutu = models.PositiveSmallIntegerField()
    sanal_aralik_saniye = models.PositiveIntegerField()
    makine_esleme_politikasi = models.CharField(max_length=32)
    hata_politikasi = models.CharField(max_length=20, default="HATADA_DEVAM")
    adim_aktif = models.BooleanField(default=False)
    aktif_claim_token = models.UUIDField(null=True)
    olusturulma_zamani = models.DateTimeField(auto_now_add=True)
    baslatilma_zamani = models.DateTimeField(null=True)
    duraklatilma_zamani = models.DateTimeField(null=True)
    tamamlanma_zamani = models.DateTimeField(null=True)
    iptal_zamani = models.DateTimeField(null=True)
    iptal_nedeni = models.CharField(max_length=500, null=True)
    son_islem_zamani = models.DateTimeField(null=True)

    class Meta:
        db_table = "replay_oturumlari"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    durum__in=(
                        "HAZIR",
                        "CALISIYOR",
                        "DURAKLATILDI",
                        "TAMAMLANDI",
                        "IPTAL_EDILDI",
                        "HATALI",
                    )
                ),
                name="replay_durum_gecerli",
            ),
            models.CheckConstraint(
                condition=Q(version__gte=1), name="replay_version_pozitif"
            ),
            models.CheckConstraint(
                condition=Q(toplam_oge__gte=1, toplam_oge__lte=1000),
                name="replay_toplam_1_1000",
            ),
            models.CheckConstraint(
                condition=Q(
                    varsayilan_batch_boyutu__gte=1, varsayilan_batch_boyutu__lte=25
                ),
                name="replay_batch_1_25",
            ),
        ]

    def __str__(self):
        return self.replay_numarasi


class ReplayOgesi(models.Model):
    class Durum(models.TextChoices):
        BEKLIYOR = "BEKLIYOR", "Bekliyor"
        ISLENIYOR = "ISLENIYOR", "İşleniyor"
        BASARILI = "BASARILI", "Başarılı"
        BASARISIZ = "BASARISIZ", "Başarısız"
        ATLANDI = "ATLANDI", "Atlandı"

    oturum = models.ForeignKey(
        ReplayOturumu, on_delete=models.CASCADE, related_name="ogeler"
    )
    sira = models.PositiveIntegerField()
    kaynak_satir_kimligi = models.PositiveIntegerField()
    external_machine_id = models.CharField(max_length=50)
    sanal_timestamp = models.DateTimeField()
    sensor_snapshot = models.JSONField()
    ground_truth_snapshot = models.JSONField()
    durum = models.CharField(
        max_length=12, choices=Durum.choices, default=Durum.BEKLIYOR
    )
    deneme_sayisi = models.PositiveSmallIntegerField(default=0)
    islem_baslangic_zamani = models.DateTimeField(null=True)
    tamamlanma_zamani = models.DateTimeField(null=True)
    hata_kodu = models.CharField(max_length=64, null=True)
    hata_mesaji = models.CharField(max_length=300, null=True)
    tahmin_kaydi = models.OneToOneField(
        TahminKaydi, on_delete=models.PROTECT, null=True, related_name="replay_ogesi"
    )
    trace_id = models.CharField(max_length=64, null=True)
    processing_token = models.UUIDField(null=True)
    islem_suresi_ms = models.FloatField(null=True)
    olusturulma_zamani = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "replay_ogeleri"
        ordering = ("sira",)
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    durum__in=(
                        "BEKLIYOR",
                        "ISLENIYOR",
                        "BASARILI",
                        "BASARISIZ",
                        "ATLANDI",
                    )
                ),
                name="replay_oge_durum_gecerli",
            ),
            models.UniqueConstraint(
                fields=("oturum", "sira"), name="replay_oge_sira_benzersiz"
            ),
            models.UniqueConstraint(
                fields=("oturum", "kaynak_satir_kimligi"),
                name="replay_oge_kaynak_benzersiz",
            ),
            models.CheckConstraint(
                condition=Q(sira__gte=1), name="replay_oge_sira_pozitif"
            ),
            models.CheckConstraint(
                condition=Q(deneme_sayisi__gte=0), name="replay_deneme_negatif_degil"
            ),
        ]


class ReplayOlayi(ImmutableSnapshotModel):
    class Tip(models.TextChoices):
        OTURUM_OLUSTURULDU = "OTURUM_OLUSTURULDU", "Oturum oluşturuldu"
        BASLATILDI = "BASLATILDI", "Başlatıldı"
        DURAKLATILDI = "DURAKLATILDI", "Duraklatıldı"
        DEVAM_ETTIRILDI = "DEVAM_ETTIRILDI", "Devam ettirildi"
        OGELER_ISLENDI = "OGELER_ISLENDI", "Öğeler işlendi"
        IPTAL_EDILDI = "IPTAL_EDILDI", "İptal edildi"
        BASARISIZLAR_YENIDEN_HAZIRLANDI = (
            "BASARISIZLAR_YENIDEN_HAZIRLANDI",
            "Başarısızlar yeniden hazırlandı",
        )

    oturum = models.ForeignKey(
        ReplayOturumu, on_delete=models.CASCADE, related_name="olaylar"
    )
    olay_tipi = models.CharField(max_length=40, choices=Tip.choices)
    gerceklestiren = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="replay_olaylari",
    )
    gerceklestiren_username_snapshot = models.CharField(max_length=150)
    trace_id = models.CharField(max_length=64)
    onceki_durum = models.CharField(max_length=16, null=True)
    yeni_durum = models.CharField(max_length=16)
    version = models.PositiveIntegerField()
    ilk_sira = models.PositiveIntegerField(null=True)
    son_sira = models.PositiveIntegerField(null=True)
    basarili_sayisi = models.PositiveIntegerField(default=0)
    basarisiz_sayisi = models.PositiveIntegerField(default=0)
    mesaj = models.CharField(max_length=300, null=True)
    olusturulma_zamani = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "replay_olaylari"
        ordering = ("olusturulma_zamani", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    olay_tipi__in=(
                        "OTURUM_OLUSTURULDU",
                        "BASLATILDI",
                        "DURAKLATILDI",
                        "DEVAM_ETTIRILDI",
                        "OGELER_ISLENDI",
                        "IPTAL_EDILDI",
                        "BASARISIZLAR_YENIDEN_HAZIRLANDI",
                    )
                ),
                name="replay_olay_tipi_gecerli",
            ),
            models.CheckConstraint(
                condition=Q(version__gte=1), name="replay_olay_version_pozitif"
            ),
            models.CheckConstraint(
                condition=Q(ilk_sira__isnull=True) | Q(ilk_sira__gte=1),
                name="replay_olay_ilk_sira_pozitif",
            ),
            models.CheckConstraint(
                condition=Q(son_sira__isnull=True) | Q(son_sira__gte=1),
                name="replay_olay_son_sira_pozitif",
            ),
        ]


class TahminReddi(ImmutableSnapshotModel):
    tahmin = models.OneToOneField(
        TahminKaydi, on_delete=models.CASCADE, related_name="red_bilgisi"
    )
    reddeden = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tahmin_redleri",
    )
    red_nedeni = models.CharField(max_length=500, null=True, blank=True)
    olusturulma_zamani = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tahmin_redleri"
