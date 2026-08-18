from django.contrib.auth.models import AbstractUser
from django.db import models


class Kullanici(AbstractUser):
    class Rol(models.TextChoices):
        USER = "USER", "Kullanıcı"
        ADMIN = "ADMIN", "Yönetici"

    rol = models.CharField(
        max_length=10,
        choices=Rol.choices,
        default=Rol.USER,
        db_index=True,
        verbose_name="rol",
    )

    class Meta:
        db_table = "kullanicilar"
        verbose_name = "kullanıcı"
        verbose_name_plural = "kullanıcılar"

    def __str__(self):
        return self.username
