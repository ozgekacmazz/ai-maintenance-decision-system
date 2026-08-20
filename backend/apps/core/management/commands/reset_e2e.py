"""Reset and verify only the explicitly isolated Sprint 21 E2E database."""

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command


class Command(BaseCommand):
    help = "Flush, migrate, seed and verify the isolated sensor_e2e database."

    def handle(self, *args, **options):
        database_name = settings.DATABASES["default"]["NAME"]
        if database_name != "sensor_e2e":
            raise CommandError(
                "Güvenlik denetimi başarısız: hedef DB tam olarak sensor_e2e olmalı."
            )

        call_command("flush", interactive=False, verbosity=0)
        call_command("migrate", interactive=False, verbosity=0)
        call_command("seed_demo", verbosity=0)

        from apps.tahminler.models import ReplayOgesi, ReplayOturumu, TahminKaydi

        demo = TahminKaydi.objects.filter(idempotency_key__startswith="demo-")
        approved = demo.filter(is_emirleri__isnull=False).distinct()
        rejected = demo.filter(red_bilgisi__isnull=False)
        inconsistent = approved.filter(red_bilgisi__isnull=False)
        pending = demo.filter(is_emirleri__isnull=True, red_bilgisi__isnull=True)
        ready_replays = ReplayOturumu.objects.filter(durum="HAZIR")
        counts = {
            "BEKLIYOR": pending.count(),
            "ONAYLANDI": approved.count(),
            "REDDEDILDI": rejected.count(),
            "TUTARSIZ": inconsistent.count(),
            "HAZIR_REPLAY": ready_replays.count(),
            "REPLAY_OGESI": ReplayOgesi.objects.filter(
                oturum__in=ready_replays
            ).count(),
        }
        expected = {
            "BEKLIYOR": 5,
            "ONAYLANDI": 4,
            "REDDEDILDI": 1,
            "TUTARSIZ": 0,
            "HAZIR_REPLAY": 1,
            "REPLAY_OGESI": 250,
        }
        if counts != expected:
            raise CommandError(f"E2E seed sözleşmesi uyuşmuyor: {counts!r}")
        self.stdout.write(self.style.SUCCESS(f"sensor_e2e hazır: {counts!r}"))
