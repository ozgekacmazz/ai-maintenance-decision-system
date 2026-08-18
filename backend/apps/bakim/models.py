from django.db import models
from django.db.models import Q

from apps.core.models import ZamanDamgaliModel


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

    class Meta:
        db_table = "ariza_parca_kurallari"
        verbose_name = "arıza-parça kuralı"
        verbose_name_plural = "arıza-parça kuralları"
        constraints = [
            models.UniqueConstraint(
                fields=("ariza_tipi", "parca"), name="ariza_parca_cifti_benzersiz"
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
