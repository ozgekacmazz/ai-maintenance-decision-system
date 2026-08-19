import os
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

from apps.bakim.models import ArizaParcaKurali, BakimIsEmri, Makine, Parca, Stok
from apps.bakim.work_order_services import (
    is_emri_ata,
    is_emri_durum_gecisi,
    is_emri_olustur,
)
from apps.kullanicilar.models import Kullanici
from apps.tahminler.exceptions import ReplayVeriSetiHatasi
from apps.tahminler.models import ReplayOturumu, TahminKaydi, TahminReddi
from apps.tahminler.record_services import tahmin_kaydi_olustur
from apps.tahminler.replay_services import (
    replay_butunlugunu_dogrula,
    replay_olustur,
)


class Command(BaseCommand):
    help = "Sunum ve demo için deterministik, tutarlı ve tekrarlanabilir demo veritabanı tohumlaması gerçekleştirir."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-demo",
            action="store_true",
            help="Önceki demo kayıtlarını silip yeniden tohumlar (destructive).",
        )

    @staticmethod
    def _env_hesaplarini_dogrula():
        if not settings.DEBUG and os.getenv("ALLOW_DEMO_SEED_IN_PRODUCTION") != "True":
            raise CommandError(
                "DEBUG=False ortamında seed_demo için "
                "ALLOW_DEMO_SEED_IN_PRODUCTION=True açık onayı gerekir."
            )

        specs = (
            (
                "admin",
                os.getenv("DEMO_ADMIN_USERNAME", "demo_admin").strip(),
                os.getenv("DEMO_ADMIN_PASSWORD", ""),
                Kullanici.Rol.ADMIN,
            ),
            (
                "user",
                os.getenv("DEMO_USER_USERNAME", "demo_operator").strip(),
                os.getenv("DEMO_USER_PASSWORD", ""),
                Kullanici.Rol.USER,
            ),
        )
        if specs[0][1] == specs[1][1]:
            raise CommandError("Demo ADMIN ve USER kullanıcı adları farklı olmalıdır.")

        for etiket, username, parola, rol in specs:
            if not username or not parola:
                raise CommandError(
                    f"Demo {etiket.upper()} kullanıcı adı ve parolası environment "
                    "üzerinden ayarlanmalıdır."
                )
            aday = Kullanici(username=username, rol=rol)
            try:
                password_validation.validate_password(parola, user=aday)
            except ValidationError as exc:
                raise CommandError(
                    f"Demo {etiket.upper()} parolası Django güvenlik kurallarını "
                    "karşılamıyor."
                ) from exc
        return specs

    def _replay_hazirla(self, *, admin_user, machine):
        try:
            session = replay_olustur(
                actor=admin_user,
                trace_id="seed-demo-replay",
                data={
                    "makine_id": machine.id,
                    "split": "test",
                    "baslangic_ofseti": 0,
                    "kayit_sayisi": 250,
                    "varsayilan_batch_boyutu": 5,
                    "sanal_aralik_saniye": 60,
                },
                idempotent=True,
            )
            actual_count = replay_butunlugunu_dogrula(session)
        except ReplayVeriSetiHatasi as exc:
            raise CommandError(
                "Demo replay hazırlanamadı: doğrulanmış prepared AI4I veri seti "
                "ve metadata dosyaları erişilebilir olmalıdır."
            ) from exc

        if actual_count < 250:
            self.stdout.write(
                self.style.WARNING(
                    f"Prepared test split'i 250 satırdan küçük; {actual_count} "
                    "gerçek replay öğesi hazırlandı."
                )
            )
        self.stdout.write(
            f"Replay demo oturumu gerçek prepared veriden HAZIR durumda oluşturuldu "
            f"({actual_count} öğe)."
        )
        return session

    @transaction.atomic
    def handle(self, *args, **options):
        login_specs = self._env_hesaplarini_dogrula()
        self.stdout.write("Demo verisi tohumlama başlatılıyor...")

        legacy_fake_replays = ReplayOturumu.objects.filter(
            replay_numarasi="REP-DEMO-2026-001",
            kaynak_veri_seti="demo_dataset",
            prepared_sha256="0" * 64,
            toplam_oge=250,
            ogeler__isnull=True,
        )
        if legacy_fake_replays.exists():
            models.QuerySet.delete(legacy_fake_replays)
            self.stdout.write("Eski placeholder demo replay kaydı temizlendi.")

        if options["reset_demo"]:
            self.stdout.write("Mevcut demo verileri temizleniyor...")
            models.QuerySet.delete(
                BakimIsEmri.objects.filter(baslik__startswith="[DEMO]")
            )
            models.QuerySet.delete(
                TahminKaydi.objects.filter(idempotency_key__startswith="demo-")
            )
            # Demo ana verileri get_or_create/update akışıyla yenilenir. Bunları silmek,
            # kullanıcı tarafından çalıştırılmış gerçek replay kayıtlarını PROTECT
            # ilişkileri üzerinden bozabilir.

        # 1. KULLANICILAR (4-6 Adet)
        users = {}
        admin_username = login_specs[0][1]
        operator_username = login_specs[1][1]
        login_passwords = {spec[1]: spec[2] for spec in login_specs}
        user_specs = [
            (admin_username, "demo_admin@factory.local", "ADMIN", True),
            (operator_username, "demo_operator@factory.local", "USER", True),
            ("demo_muhendis", "demo_muhendis@factory.local", "USER", True),
            ("demo_stajyer", "demo_stajyer@factory.local", "USER", True),
            ("demo_pasif", "demo_pasif@factory.local", "USER", False),
        ]
        for username, email, rol, is_active in user_specs:
            u, created = Kullanici.objects.get_or_create(
                username=username,
                defaults={"email": email, "rol": rol, "is_active": is_active},
            )
            if not created and u.email != email:
                raise CommandError(
                    f"'{username}' mevcut ancak canonical demo hesabı değil; "
                    "kullanıcı verisi değiştirilmedi."
                )
            if u.rol != rol or u.is_active != is_active:
                u.rol = rol
                u.is_active = is_active
                u.save()
            if username in login_passwords:
                parola = login_passwords[username]
                if not u.check_password(parola):
                    u.set_password(parola)
                    u.save(update_fields=("password",))
            elif created:
                u.set_unusable_password()
                u.save(update_fields=("password",))
            users[username] = u
        self.stdout.write(f"Kullanıcılar hazırlandı ({len(users)} adet).")

        admin_user = users[admin_username]
        operator_user = users[operator_username]

        # 2. MAKİNELER (8-10 Adet)
        machines = []
        machine_specs = [
            ("M-DEMO-101", "Pres Motoru 1", 5, True),
            ("M-DEMO-102", "Pompa Motoru 2", 4, True),
            ("M-DEMO-103", "Ana Mil Fanı 3", 3, True),
            ("M-DEMO-104", "Soğutma Kompresörü 4", 5, True),
            ("M-DEMO-105", "Konveyör Bant Motoru 5", 2, True),
            ("M-DEMO-106", "Hidrolik Güç Ünitesi 6", 4, True),
            ("M-DEMO-107", "CMM Hava Kurutucu 7", 1, True),
            ("M-DEMO-108", "CNC Torna Ana Spindle 8", 5, True),
            ("M-DEMO-109", "Yedek Filtreleme Hattı 9", 2, False),
        ]
        for kod, ad, kritiklik, aktif in machine_specs:
            m, _ = Makine.objects.get_or_create(
                makine_kodu=kod,
                defaults={"ad": ad, "kritiklik": kritiklik, "aktif": aktif},
            )
            if m.ad != ad or m.kritiklik != kritiklik or m.aktif != aktif:
                m.ad = ad
                m.kritiklik = kritiklik
                m.aktif = aktif
                m.save()
            machines.append(m)
        self.stdout.write(f"Makineler hazırlandı ({len(machines)} adet).")

        # 3. PARÇALAR VE STOK (8-12 Adet)
        part_specs = [
            ("PRC-DEMO-01", "Güç Rölesi 24V", 10, 2, 3),  # Normal Stok
            ("PRC-DEMO-02", "Termal Yağ Filtresi", 1, 2, 5),  # Düşük Stok
            ("PRC-DEMO-03", "Yüksek Basınç Hortumu", 0, 3, 7),  # Stok = 0
            ("PRC-DEMO-04", "Rulman Takımı 6205", 15, 5, 2),  # Normal
            ("PRC-DEMO-05", "Spindle Sızdırmazlık Contası", 2, 2, 4),  # Kritik Eşikte
            ("PRC-DEMO-06", "Kompresör Fan Kanadı", 0, 1, 14),  # Stok = 0, Uzun Tedarik
            ("PRC-DEMO-07", "Hidrolik Valf Bloğu", 5, 1, 3),  # Normal
            ("PRC-DEMO-08", "Sensör Kablosu M12", 20, 5, 1),  # Bol Stok
        ]
        for parca_kodu, ad, adet, min_stok, tedarik_gun in part_specs:
            p, _ = Parca.objects.get_or_create(
                parca_kodu=parca_kodu,
                defaults={"ad": ad, "aktif": True},
            )
            stok, _ = Stok.objects.get_or_create(
                parca=p,
                defaults={
                    "adet": adet,
                    "minimum_stok": min_stok,
                    "tedarik_gun": tedarik_gun,
                },
            )
            if (
                stok.adet != adet
                or stok.minimum_stok != min_stok
                or stok.tedarik_gun != tedarik_gun
            ):
                stok.adet = adet
                stok.minimum_stok = min_stok
                stok.tedarik_gun = tedarik_gun
                stok.save()

            # ArizaParcaKurali tanımları
            ariza_tipleri = ["HDF", "PWF", "OSF", "TWF"]
            for index, ariza in enumerate(ariza_tipleri, start=1):
                ArizaParcaKurali.objects.get_or_create(
                    ariza_tipi=ariza,
                    parca=p,
                    defaults={
                        "tercih_sirasi": index,
                        "gerekli_miktar": 1,
                        "onerilen_aksiyon": f"{ad} kontrolü ve değişimi.",
                        "aktif": True,
                    },
                )
        self.stdout.write("Parçalar, stok ve arıza kuralları hazırlandı.")

        # 4. TAHMİN KAYITLARI (12-20 Kayıt)
        prediction_configs = [
            # (makine_idx, kaynak, ikey, temp_k, proc_k, rpm, torque_nm, wear_min, time_offset_hours)
            (
                0,
                "MANUEL",
                "demo-pred-01",
                300.2,
                310.5,
                1500,
                45.0,
                180,
                24,
            ),  # OSF / Riskli
            (
                0,
                "MANUEL",
                "demo-pred-02",
                304.5,
                315.8,
                1350,
                62.0,
                210,
                18,
            ),  # HDF / Kritik
            (
                1,
                "MANUEL",
                "demo-pred-03",
                298.1,
                308.2,
                1420,
                38.0,
                45,
                16,
            ),  # Düşük Risk / Temiz
            (
                1,
                "MANUEL",
                "demo-pred-04",
                302.8,
                312.4,
                1280,
                58.0,
                195,
                12,
            ),  # Riskli / PWF
            (
                2,
                "MANUEL",
                "demo-pred-05",
                299.0,
                309.0,
                1600,
                32.0,
                20,
                10,
            ),  # Düşük Risk
            (
                3,
                "MANUEL",
                "demo-pred-06",
                305.1,
                316.2,
                1200,
                68.0,
                220,
                8,
            ),  # Yüksek Risk
            (
                3,
                "MANUEL",
                "demo-pred-07",
                301.0,
                311.0,
                1480,
                42.0,
                90,
                6,
            ),  # Düşük Risk
            (
                4,
                "MANUEL",
                "demo-pred-08",
                303.4,
                314.1,
                1300,
                55.0,
                175,
                4,
            ),  # Orta Risk
            (
                5,
                "MANUEL",
                "demo-pred-09",
                298.5,
                308.5,
                1520,
                35.0,
                10,
                2,
            ),  # Düşük Risk
            (
                7,
                "MANUEL",
                "demo-pred-10",
                304.8,
                315.5,
                1250,
                65.0,
                205,
                1,
            ),  # Yüksek Risk
        ]

        base_time = datetime(2026, 8, 19, 10, 0, 0, tzinfo=dt_timezone.utc)
        created_predictions = []
        for (
            m_idx,
            kaynak,
            ikey,
            air_k,
            proc_k,
            rpm,
            torque,
            wear,
            offset,
        ) in prediction_configs:
            makine = machines[m_idx]
            rec_time = base_time - timedelta(hours=offset)
            sensor_data = {
                "urun_tipi": "M",
                "hava_sicakligi_k": air_k,
                "proses_sicakligi_k": proc_k,
                "donus_hizi_rpm": rpm,
                "tork_nm": torque,
                "takim_asinmasi_dk": wear,
            }
            pred, _ = tahmin_kaydi_olustur(
                kullanici=operator_user,
                trace_id=f"trace-{ikey}",
                veriler={
                    "makine_id": makine.id,
                    "olcum_zamani": rec_time,
                    "kaynak": kaynak,
                    "idempotency_key": ikey,
                    "sensor_verisi": sensor_data,
                },
            )
            created_predictions.append(pred)
        self.stdout.write(
            f"Tahmin kayıtları hazırlandı ({len(created_predictions)} adet)."
        )

        # 5. ONAY / RED SENARYOLARI (Demo Zincirleri)
        # Senaryo 1: Pres Motoru 1 -> ONAYLANDI -> İş Emri Oluşturuldu
        pred_approved = created_predictions[1]  # HDF Kritik
        wo_1, rep_1 = is_emri_olustur(
            actor=operator_user,
            trace_id="trace-wo-demo-1",
            veriler={
                "tahmin_kaydi_id": str(pred_approved.id),
                "baslik": "[DEMO] Pres Motoru 1 Termal Yağ Filtresi Değişimi",
                "aciklama": "Model HDF uyarısı verdi. ERP stokta 1 adet parca mevcut, öncelikli bakım onaylandı.",
                "idempotency_key": "wo-demo-key-1",
            },
        )
        if not rep_1:
            is_emri_ata(
                order_id=wo_1.id,
                actor=admin_user,
                trace_id="trace-wo-demo-1-ata",
                expected_version=wo_1.version,
                assignee=operator_user,
                note="Acil müdahale ekibine atandı.",
            )
            is_emri_durum_gecisi(
                order_id=wo_1.id,
                actor=operator_user,
                trace_id="trace-wo-demo-1-gecis",
                expected_version=wo_1.version + 1,
                target="DEVAM_EDIYOR",
                data={},
            )

        # Senaryo 2: Pompa Motoru 2 -> REDDEDİLDİ -> Reddeden kullanıcı & nedeni kaydedildi, İş Emri YOK
        pred_rejected = created_predictions[3]  # PWF
        if not hasattr(pred_rejected, "red_bilgisi"):
            TahminReddi.objects.create(
                tahmin=pred_rejected,
                reddeden=operator_user,
                red_nedeni="Saha incelemesinde sensör kalibrasyon hatası tespit edildi, bakım gereksiz görüldü.",
            )

        # Senaryo 3: Diğer Tahminler için İş Emirleri (Farklı Durumlar ve SLA Çeşitliliği)
        pred_wo_2 = created_predictions[0]  # OSF
        wo_2, _ = is_emri_olustur(
            actor=operator_user,
            trace_id="trace-wo-demo-2",
            veriler={
                "tahmin_kaydi_id": str(pred_wo_2.id),
                "baslik": "[DEMO] Pres Motoru 1 Yüksek Basınç Hortumu Kontrolü",
                "aciklama": "Aşırı tork uyarısı üzerine oluşturulan açık iş emri.",
                "idempotency_key": "wo-demo-key-2",
            },
        )

        pred_wo_3 = created_predictions[5]  # Soğutma Kompresörü
        wo_3, rep_3 = is_emri_olustur(
            actor=operator_user,
            trace_id="trace-wo-demo-3",
            veriler={
                "tahmin_kaydi_id": str(pred_wo_3.id),
                "baslik": "[DEMO] Soğutma Kompresörü Kanat Değişimi",
                "aciklama": "Stok 0 olduğu için beklemede olan iş emri.",
                "idempotency_key": "wo-demo-key-3",
            },
        )
        if not rep_3:
            is_emri_ata(
                order_id=wo_3.id,
                actor=admin_user,
                trace_id="trace-wo-demo-3-ata",
                expected_version=wo_3.version,
                assignee=operator_user,
                note="Parça tedariği bekleniyor.",
            )
            is_emri_durum_gecisi(
                order_id=wo_3.id,
                actor=operator_user,
                trace_id="trace-wo-demo-3-gecis",
                expected_version=wo_3.version + 1,
                target="BEKLEMEDE",
                data={
                    "bekleme_nedeni": "PRC-DEMO-06 tedarik süresi 14 gün, stok 0 olduğu için sipariş geçildi."
                },
            )

        pred_wo_4 = created_predictions[7]  # Konveyör
        wo_4, rep_4 = is_emri_olustur(
            actor=operator_user,
            trace_id="trace-wo-demo-4",
            veriler={
                "tahmin_kaydi_id": str(pred_wo_4.id),
                "baslik": "[DEMO] Konveyör Motoru Rulman Revizyonu",
                "aciklama": "Tamamlanan revizyon iş emri.",
                "idempotency_key": "wo-demo-key-4",
            },
        )
        if not rep_4:
            is_emri_ata(
                order_id=wo_4.id,
                actor=admin_user,
                trace_id="trace-wo-demo-4-ata",
                expected_version=wo_4.version,
                assignee=operator_user,
                note="Atandı.",
            )
            is_emri_durum_gecisi(
                order_id=wo_4.id,
                actor=operator_user,
                trace_id="trace-wo-demo-4-gecis1",
                expected_version=wo_4.version + 1,
                target="DEVAM_EDIYOR",
                data={},
            )
            is_emri_durum_gecisi(
                order_id=wo_4.id,
                actor=operator_user,
                trace_id="trace-wo-demo-4-gecis2",
                expected_version=wo_4.version + 2,
                target="TAMAMLANDI",
                data={
                    "tamamlama_notu": "Rulman değişimi tamamlandı, titreşim değerleri normale döndü."
                },
            )

        self.stdout.write("İş emirleri ve onay/red durumları başarıyla oluşturuldu.")

        # 6. GERÇEK PREPARED VERİDEN REPLAY OTURUMU
        replay_session = self._replay_hazirla(
            admin_user=admin_user, machine=machines[0]
        )

        demo_predictions = TahminKaydi.objects.filter(
            idempotency_key__startswith="demo-"
        )
        onaylanan = demo_predictions.filter(is_emirleri__isnull=False).distinct()
        reddedilen = demo_predictions.filter(red_bilgisi__isnull=False)
        tutarsiz = onaylanan.filter(red_bilgisi__isnull=False)
        bekleyen = demo_predictions.filter(
            is_emirleri__isnull=True, red_bilgisi__isnull=True
        )
        demo_orders = BakimIsEmri.objects.filter(baslik__startswith="[DEMO]")
        replay_oge_sayisi = replay_session.ogeler.count()
        if (
            tutarsiz.exists()
            or not bekleyen.exists()
            or not onaylanan.exists()
            or not reddedilen.exists()
            or not demo_orders.exists()
            or replay_session.durum != ReplayOturumu.Durum.HAZIR
            or replay_oge_sayisi == 0
        ):
            raise CommandError("Demo veri bütünlüğü doğrulanamadı; işlem geri alındı.")

        self.stdout.write("Demo ADMIN hesabı hazır.")
        self.stdout.write("Demo USER hesabı hazır.")
        self.stdout.write(
            "Bütünlük özeti: "
            f"{len(machines)} makine, {demo_predictions.count()} tahmin, "
            f"{bekleyen.count()} bekleyen, {onaylanan.count()} onaylanan, "
            f"{reddedilen.count()} reddedilen, {demo_orders.count()} iş emri, "
            f"HAZIR replay {replay_oge_sayisi} gerçek öğe."
        )

        self.stdout.write(
            self.style.SUCCESS(
                "✓ Sunum ve demo veritabanı tohumlaması BAŞARIYLA TAMAMLANDI."
            )
        )
