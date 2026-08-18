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


class ImmutableSnapshotQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValueError("Geçmiş snapshot toplu olarak değiştirilemez.")

    def delete(self):
        raise ValueError("Geçmiş snapshot toplu olarak silinemez.")


class ImmutableSnapshotModel(models.Model):
    objects = ImmutableSnapshotQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("Geçmiş snapshot değiştirilemez.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Geçmiş snapshot silinemez.")
