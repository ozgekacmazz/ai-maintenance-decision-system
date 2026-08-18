from django.db import models


class ZamanDamgaliModel(models.Model):
    olusturulma_tarihi = models.DateTimeField(
        auto_now_add=True, verbose_name="oluşturulma tarihi"
    )
    guncellenme_tarihi = models.DateTimeField(
        auto_now=True, verbose_name="güncellenme tarihi"
    )

    class Meta:
        abstract = True
