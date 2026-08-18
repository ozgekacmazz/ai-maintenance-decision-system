import os

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Environment değişkenlerinden geliştirme/demo yöneticisi oluşturur."

    def add_arguments(self, parser):
        parser.add_argument(
            "--update-password",
            action="store_true",
            help="Mevcut bootstrap yöneticisinin parolasını environment değeriyle yeniler.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME", "").strip()
        email = os.getenv("ADMIN_EMAIL", "").strip()
        password = os.getenv("ADMIN_PASSWORD", "")

        if not username:
            raise CommandError("ADMIN_USERNAME environment değişkeni zorunludur.")
        if not password:
            raise CommandError("ADMIN_PASSWORD environment değişkeni zorunludur.")

        kullanici_modeli = get_user_model()
        normalized_username = kullanici_modeli.normalize_username(username)
        kullanici = (
            kullanici_modeli.objects.select_for_update()
            .filter(username=normalized_username)
            .first()
        )

        if kullanici is None:
            aday = kullanici_modeli(
                username=normalized_username,
                email=kullanici_modeli.objects.normalize_email(email),
            )
            self._parolayi_dogrula(password, aday)
            kullanici = kullanici_modeli.objects.create_superuser(
                username=normalized_username,
                email=email,
                password=password,
                rol=kullanici_modeli.Rol.ADMIN,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Bootstrap yöneticisi oluşturuldu: {kullanici.username}"
                )
            )
            return

        kullanici.rol = kullanici_modeli.Rol.ADMIN
        kullanici.is_active = True
        kullanici.is_staff = True
        kullanici.is_superuser = True
        guncellenen_alanlar = ["rol", "is_active", "is_staff", "is_superuser"]

        if email:
            kullanici.email = kullanici_modeli.objects.normalize_email(email)
            guncellenen_alanlar.append("email")
        if options["update_password"]:
            self._parolayi_dogrula(password, kullanici)
            kullanici.set_password(password)
            guncellenen_alanlar.append("password")

        kullanici.save(update_fields=guncellenen_alanlar)
        self.stdout.write(
            self.style.SUCCESS(
                f"Bootstrap yöneticisi zaten mevcut/güncellendi: {kullanici.username}"
            )
        )

    @staticmethod
    def _parolayi_dogrula(password, kullanici):
        try:
            password_validation.validate_password(password, user=kullanici)
        except ValidationError as exc:
            raise CommandError(
                "ADMIN_PASSWORD güvenlik kurallarını karşılamıyor."
            ) from exc
