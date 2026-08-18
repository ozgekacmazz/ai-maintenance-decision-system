import json
import time
import uuid
from copy import deepcopy
from datetime import timedelta

import pandas as pd
from bakim_ml.loaders import DatasetLoadError, load_prepared_dataset
from bakim_ml.training import split_dataset
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.bakim.models import Makine
from apps.tahminler.exceptions import ReplayCakismasiHatasi, ReplayVeriSetiHatasi
from apps.tahminler.models import ReplayOgesi, ReplayOlayi, ReplayOturumu
from apps.tahminler.record_services import tahmin_kaydi_olustur
from apps.tahminler.replay_policy import (
    CLAIM_TIMEOUT_SECONDS,
    MAX_ATTEMPTS,
    REPLAY_POLICY_VERSION,
    ReplayPolitikaHatasi,
    gecisi_dogrula,
    snapshots_from_row,
)


def _event(session, actor, trace_id, kind, old=None, **extra):
    return ReplayOlayi.objects.create(
        oturum=session,
        olay_tipi=kind,
        gerceklestiren=actor,
        gerceklestiren_username_snapshot=actor.username,
        trace_id=trace_id,
        onceki_durum=old,
        yeni_durum=session.durum,
        version=session.version,
        **extra,
    )


def _load_selected(*, split, offset, count):
    try:
        metadata = json.loads(
            settings.REPLAY_PREPARED_METADATA_PATH.read_text(encoding="utf-8")
        )
        checksum = metadata["prepared_source_sha256"]
        frame = load_prepared_dataset(
            settings.REPLAY_PREPARED_DATASET_PATH, expected_sha256=checksum
        )
        parts = dict(
            zip(("train", "validation", "test"), split_dataset(frame), strict=True)
        )
        selected = frame if split == "all" else parts[split]
        selected = selected.assign(
            _timestamp=pd.to_datetime(selected["timestamp"], utc=True),
            _source_index=selected.index,
        ).sort_values(["_timestamp", "_source_index"])
    except (OSError, ValueError, KeyError, DatasetLoadError) as exc:
        raise ReplayVeriSetiHatasi() from exc
    return selected.iloc[offset : offset + count], checksum


def replay_olustur(*, actor, trace_id, data):
    values = deepcopy(data)
    machine = Makine.objects.filter(pk=values["makine_id"], aktif=True).first()
    if not machine:
        raise ReplayCakismasiHatasi(
            "REPLAY_MAKINE_ESLEMESI_GECERSIZ", "Aktif replay makinesi bulunamadı."
        )
    selected, checksum = _load_selected(
        split=values["split"],
        offset=values["baslangic_ofseti"],
        count=values["kayit_sayisi"],
    )
    if selected.empty:
        raise ReplayCakismasiHatasi(
            "REPLAY_MAKINE_ESLEMESI_GECERSIZ", "Seçim replay öğesi üretmedi."
        )
    now = timezone.now()
    with transaction.atomic():
        session = ReplayOturumu(
            olusturan=actor,
            makine=machine,
            politika_surumu=REPLAY_POLICY_VERSION,
            kaynak_veri_seti="ai4i2020_prepared",
            prepared_sha256=checksum,
            split=values["split"],
            baslangic_ofseti=values["baslangic_ofseti"],
            toplam_oge=len(selected),
            varsayilan_batch_boyutu=values["varsayilan_batch_boyutu"],
            sanal_aralik_saniye=values["sanal_aralik_saniye"],
            makine_esleme_politikasi="TEK_MAKINE",
        )
        session.replay_numarasi = f"RP-{now.year}-{session.id.hex[:12].upper()}"
        session.save(force_insert=True)
        items = []
        for sequence, (_, row) in enumerate(selected.iterrows(), start=1):
            sensor, truth = snapshots_from_row(row)
            items.append(
                ReplayOgesi(
                    oturum=session,
                    sira=sequence,
                    kaynak_satir_kimligi=int(row["_source_index"]),
                    external_machine_id=str(row["machine_id"]),
                    sanal_timestamp=row["_timestamp"].to_pydatetime(),
                    sensor_snapshot=sensor,
                    ground_truth_snapshot=truth,
                )
            )
        ReplayOgesi.objects.bulk_create(items)
        _event(session, actor, trace_id, "OTURUM_OLUSTURULDU")
    return session


def replay_gecis(*, session_id, actor, trace_id, expected_version, target, reason=None):
    with transaction.atomic():
        session = (
            ReplayOturumu.objects.select_for_update().filter(pk=session_id).first()
        )
        if not session:
            from rest_framework.exceptions import NotFound

            raise NotFound("Replay oturumu bulunamadı.")
        if session.version != expected_version:
            raise ReplayCakismasiHatasi(
                "REPLAY_ESZAMANLI_GUNCELLEME_CAKISMASI", "Replay oturumu güncellendi."
            )
        try:
            gecisi_dogrula(session.durum, target)
        except ReplayPolitikaHatasi as exc:
            raise ReplayCakismasiHatasi(
                "REPLAY_DURUM_GECISI_GECERSIZ", str(exc)
            ) from exc
        old, now = session.durum, timezone.now()
        session.durum = target
        session.version += 1
        if target == "CALISIYOR":
            session.baslatilma_zamani = session.baslatilma_zamani or now
        elif target == "DURAKLATILDI":
            session.duraklatilma_zamani = now
        elif target == "IPTAL_EDILDI":
            if not str(reason or "").strip():
                raise ReplayCakismasiHatasi(
                    "REPLAY_DURUM_GECISI_GECERSIZ", "İptal nedeni zorunludur."
                )
            session.iptal_zamani, session.iptal_nedeni = now, reason.strip()
        session.save()
        event = {
            "CALISIYOR": "BASLATILDI" if old == "HAZIR" else "DEVAM_ETTIRILDI",
            "DURAKLATILDI": "DURAKLATILDI",
            "IPTAL_EDILDI": "IPTAL_EDILDI",
        }[target]
        _event(session, actor, trace_id, event, old=old, mesaj=reason)
        return session


def _claim(*, session_id, actor, trace_id, expected_version, batch_size, now):
    with transaction.atomic():
        session = ReplayOturumu.objects.select_for_update().get(pk=session_id)
        if session.version != expected_version:
            raise ReplayCakismasiHatasi(
                "REPLAY_ESZAMANLI_GUNCELLEME_CAKISMASI", "Replay oturumu güncellendi."
            )
        if session.durum != "CALISIYOR":
            raise ReplayCakismasiHatasi(
                "REPLAY_DURUM_GECISI_GECERSIZ",
                "Replay adımı yalnız çalışan oturumda çalışır.",
            )
        cutoff = now - timedelta(seconds=CLAIM_TIMEOUT_SECONDS)
        stale = session.ogeler.filter(
            durum="ISLENIYOR", islem_baslangic_zamani__lte=cutoff
        )
        stale.update(durum="BEKLIYOR", processing_token=None)
        if session.adim_aktif and session.ogeler.filter(durum="ISLENIYOR").exists():
            raise ReplayCakismasiHatasi(
                "REPLAY_ADIMI_ZATEN_CALISIYOR", "Replay adımı zaten çalışıyor."
            )
        token = uuid.uuid4()
        items = list(
            session.ogeler.select_for_update(skip_locked=True)
            .filter(durum="BEKLIYOR", deneme_sayisi__lt=MAX_ATTEMPTS)
            .order_by("sira")[:batch_size]
        )
        for item in items:
            item.durum, item.processing_token = "ISLENIYOR", token
            item.islem_baslangic_zamani, item.deneme_sayisi = (
                now,
                item.deneme_sayisi + 1,
            )
        ReplayOgesi.objects.bulk_update(
            items,
            ("durum", "processing_token", "islem_baslangic_zamani", "deneme_sayisi"),
        )
        session.adim_aktif, session.aktif_claim_token = True, token
        session.version += 1
        session.save()
        return session, items, token


def _finalize_success(*, item_id, token, prediction, trace_id, started):
    with transaction.atomic():
        item = ReplayOgesi.objects.select_for_update().get(pk=item_id)
        if item.durum != "ISLENIYOR" or item.processing_token != token:
            return False
        item.durum, item.tahmin_kaydi = "BASARILI", prediction
        item.tamamlanma_zamani, item.trace_id = timezone.now(), trace_id
        item.islem_suresi_ms = round((time.perf_counter() - started) * 1000, 3)
        item.processing_token = None
        item.save()
        return True


def replay_adim(*, session_id, actor, trace_id, expected_version, batch_size, now=None):
    now = now or timezone.now()
    session, items, token = _claim(
        session_id=session_id,
        actor=actor,
        trace_id=trace_id,
        expected_version=expected_version,
        batch_size=batch_size,
        now=now,
    )
    successes = failures = 0
    for item in items:
        started = time.perf_counter()
        try:
            prediction, _ = tahmin_kaydi_olustur(
                kullanici=actor,
                trace_id=trace_id,
                veriler={
                    "makine_id": session.makine_id,
                    "olcum_zamani": item.sanal_timestamp,
                    "kaynak": "REPLAY",
                    "idempotency_key": f"replay:{session.id}:{item.sira}",
                    "sensor_verisi": deepcopy(item.sensor_snapshot),
                },
            )
            if _finalize_success(
                item_id=item.pk,
                token=token,
                prediction=prediction,
                trace_id=trace_id,
                started=started,
            ):
                successes += 1
        except Exception:
            with transaction.atomic():
                locked = ReplayOgesi.objects.select_for_update().get(pk=item.pk)
                if locked.processing_token == token:
                    locked.durum, locked.hata_kodu = (
                        "BASARISIZ",
                        "TAHMIN_ISLEMI_BASARISIZ",
                    )
                    locked.hata_mesaji = "Replay öğesi güvenli biçimde işlenemedi."
                    locked.tamamlanma_zamani, locked.trace_id = timezone.now(), trace_id
                    locked.processing_token = None
                    locked.save()
            failures += 1
    with transaction.atomic():
        session = ReplayOturumu.objects.select_for_update().get(pk=session_id)
        if session.aktif_claim_token == token:
            session.adim_aktif, session.aktif_claim_token = False, None
            session.son_islem_zamani = timezone.now()
            if not session.ogeler.filter(durum__in=("BEKLIYOR", "ISLENIYOR")).exists():
                old, session.durum = session.durum, "TAMAMLANDI"
                session.tamamlanma_zamani = timezone.now()
            else:
                old = session.durum
            session.save()
            _event(
                session,
                actor,
                trace_id,
                "OGELER_ISLENDI",
                old=old,
                ilk_sira=items[0].sira if items else None,
                son_sira=items[-1].sira if items else None,
                basarili_sayisi=successes,
                basarisiz_sayisi=failures,
            )
    return session, successes, failures


def basarisizlari_yeniden_dene(*, session_id, actor, trace_id, expected_version):
    with transaction.atomic():
        session = ReplayOturumu.objects.select_for_update().get(pk=session_id)
        if session.version != expected_version:
            raise ReplayCakismasiHatasi(
                "REPLAY_ESZAMANLI_GUNCELLEME_CAKISMASI", "Replay oturumu güncellendi."
            )
        count = session.ogeler.filter(
            durum="BASARISIZ", deneme_sayisi__lt=MAX_ATTEMPTS
        ).update(durum="BEKLIYOR", hata_kodu=None, hata_mesaji=None)
        session.version += 1
        if session.durum == "TAMAMLANDI" and count:
            session.durum = "HATALI"
        session.save()
        _event(
            session,
            actor,
            trace_id,
            "BASARISIZLAR_YENIDEN_HAZIRLANDI",
            mesaj=f"{count} öğe",
        )
        return session, count
