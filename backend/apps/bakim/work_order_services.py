import hashlib
import json
from copy import deepcopy

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.bakim.exceptions import (
    EszamanliGuncellemeHatasi,
    IsEmriCakismasiHatasi,
    IsEmriGecisiHatasi,
)
from apps.bakim.models import BakimIsEmri, IsEmriOlayi
from apps.bakim.work_order_policy import (
    ACTIVE_STATES,
    WORK_ORDER_POLICY_VERSION,
    IsEmriPolitikaHatasi,
    gecisi_dogrula,
    genel_oncelik_hedef_mudahale_zamani,
    hedef_mudahale_zamani,
)
from apps.kullanicilar.models import Kullanici
from apps.tahminler.models import TahminKaydi


def _fingerprint(data):
    canonical = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _olay(
    *,
    order,
    actor,
    trace_id,
    event_type,
    old_state=None,
    description=None,
    old_assignee=None,
    new_assignee=None,
    old_priority=None,
    new_priority=None,
    old_general_priority=None,
    new_general_priority=None,
):
    return IsEmriOlayi.objects.create(
        is_emri=order,
        olay_tipi=event_type,
        onceki_durum=old_state,
        yeni_durum=order.durum,
        gerceklestiren=actor,
        gerceklestiren_username_snapshot=actor.username,
        trace_id=trace_id,
        aciklama_snapshot=description,
        onceki_atanan_username_snapshot=getattr(old_assignee, "username", None),
        yeni_atanan_username_snapshot=getattr(new_assignee, "username", None),
        onceki_oncelik=old_priority,
        yeni_oncelik=new_priority,
        onceki_genel_oncelik=old_general_priority,
        yeni_genel_oncelik=new_general_priority,
        version=order.version,
    )


def _number(order_id, created_at):
    return f"WO-{created_at.year}-{order_id.hex[:12].upper()}"


def _canonical_karar_degerleri(decision):
    canonical_fields = (
        decision.genel_oncelik,
        decision.stok_katsayisi,
        decision.ham_genel_oncelik,
        decision.genel_oncelik_formul_surumu,
    )
    if all(value is None for value in canonical_fields):
        return None, None, None
    if any(value is None for value in canonical_fields):
        raise IsEmriCakismasiHatasi(
            "IS_EMRI_CANONICAL_KARAR_GECERSIZ",
            "Bakım kararının genel öncelik bilgileri eksik veya tutarsızdır.",
        )
    return (
        decision.genel_oncelik,
        decision.genel_oncelik_formul_surumu,
        decision.genel_oncelik,
    )


def _is_emri_oncelik_turu(order):
    canonical_fields = (
        order.kaynak_genel_oncelik,
        order.kaynak_genel_oncelik_formul_surumu,
        order.etkin_genel_oncelik,
    )
    if all(value is None for value in canonical_fields):
        return "legacy"
    if all(value is not None for value in canonical_fields):
        return "canonical"
    raise IsEmriCakismasiHatasi(
        "IS_EMRI_CANONICAL_ALANLAR_TUTARSIZ",
        "İş emrinin genel öncelik bilgileri eksik veya tutarsızdır.",
    )


def is_emri_olustur(*, actor, trace_id, veriler):
    data = deepcopy(veriler)
    prediction_id = str(data["tahmin_kaydi_id"])
    fingerprint = _fingerprint(
        {
            "tahmin_kaydi_id": prediction_id,
            "baslik": data["baslik"],
            "aciklama": data["aciklama"],
        }
    )
    existing = BakimIsEmri.objects.filter(
        olusturan=actor, idempotency_key=data["idempotency_key"]
    ).first()
    if existing:
        if existing.payload_fingerprint != fingerprint:
            raise IsEmriCakismasiHatasi(
                "IDEMPOTENCY_CAKISMASI",
                "Idempotency anahtarı farklı istek için kullanılmış.",
            )
        return existing, True
    try:
        with transaction.atomic():
            prediction = (
                TahminKaydi.objects.select_for_update()
                .select_related("makine")
                .filter(pk=data["tahmin_kaydi_id"])
                .first()
            )
            if not prediction:
                raise NotFound("Tahmin kaydı bulunamadı.")
            if hasattr(prediction, "red_bilgisi"):
                raise IsEmriCakismasiHatasi(
                    "TAHMIN_REDDEDILMIS",
                    "Bu tahmin kullanıcı tarafından reddedilmiştir, iş emri oluşturulamaz.",
                )
            if prediction.kaynak == TahminKaydi.Kaynak.REPLAY:
                raise IsEmriCakismasiHatasi(
                    "REPLAY_TAHMININDEN_IS_EMRI_OLUSTURULAMAZ",
                    "Replay tahmininden iş emri oluşturulamaz.",
                )
            existing = BakimIsEmri.objects.filter(
                olusturan=actor, idempotency_key=data["idempotency_key"]
            ).first()
            if existing:
                if existing.payload_fingerprint != fingerprint:
                    raise IsEmriCakismasiHatasi(
                        "IDEMPOTENCY_CAKISMASI",
                        "Idempotency anahtarı farklı istek için kullanılmış.",
                    )
                return existing, True
            try:
                decision = prediction.bakim_karari
            except TahminKaydi.bakim_karari.RelatedObjectDoesNotExist as exc:
                raise IsEmriCakismasiHatasi(
                    "IS_EMRI_KARARI_BULUNAMADI", "Tahmin için bakım kararı bulunmuyor."
                ) from exc
            if BakimIsEmri.objects.filter(
                tahmin_kaydi=prediction, durum__in=ACTIVE_STATES
            ).exists():
                raise IsEmriCakismasiHatasi(
                    "IS_EMRI_AKTIF_KAYIT_MEVCUT",
                    "Tahmin için aktif iş emri zaten mevcut.",
                )
            now = timezone.now()
            (
                kaynak_genel_oncelik,
                kaynak_genel_oncelik_formul_surumu,
                etkin_genel_oncelik,
            ) = _canonical_karar_degerleri(decision)
            try:
                if kaynak_genel_oncelik is None:
                    deadline = hedef_mudahale_zamani(
                        baslangic=now, oncelik=decision.oncelik_seviyesi
                    )
                else:
                    deadline = genel_oncelik_hedef_mudahale_zamani(
                        baslangic=now, genel_oncelik=kaynak_genel_oncelik
                    )
            except IsEmriPolitikaHatasi as exc:
                raise IsEmriCakismasiHatasi(
                    "IS_EMRI_CANONICAL_SLA_GECERSIZ",
                    "İş emri genel öncelik SLA bilgisi geçersizdir.",
                ) from exc
            order = BakimIsEmri(
                tahmin_kaydi=prediction,
                makine=prediction.makine,
                olusturan=actor,
                durum=BakimIsEmri.Durum.ACIK,
                baslik=data["baslik"],
                aciklama=data["aciklama"],
                idempotency_key=data["idempotency_key"],
                payload_fingerprint=fingerprint,
                politika_surumu=WORK_ORDER_POLICY_VERSION,
                kaynak_motor_surumu=decision.motor_surumu,
                kaynak_teknik_aciliyet_skoru=decision.teknik_aciliyet_skoru,
                kaynak_tedarik_riski_skoru=decision.tedarik_riski_skoru,
                kaynak_nihai_oncelik_skoru=decision.nihai_oncelik_skoru,
                kaynak_oncelik_seviyesi=decision.oncelik_seviyesi,
                kaynak_genel_oncelik=kaynak_genel_oncelik,
                kaynak_genel_oncelik_formul_surumu=(kaynak_genel_oncelik_formul_surumu),
                kaynak_ana_aksiyon=decision.ana_aksiyon,
                kaynak_karar_guveni=decision.karar_guveni,
                kaynak_ana_ariza_tipi=decision.ana_ariza_tipi,
                etkin_oncelik_seviyesi=decision.oncelik_seviyesi,
                etkin_genel_oncelik=etkin_genel_oncelik,
                hedef_mudahale_zamani=deadline,
                olusturulma_zamani=now,
            )
            order.is_emri_numarasi = _number(order.id, now)
            order.save(force_insert=True)
            _olay(order=order, actor=actor, trace_id=trace_id, event_type="OLUSTURULDU")
            return order, False
    except IntegrityError as exc:
        existing = BakimIsEmri.objects.filter(
            olusturan=actor, idempotency_key=data["idempotency_key"]
        ).first()
        if existing and existing.payload_fingerprint == fingerprint:
            return existing, True
        raise IsEmriCakismasiHatasi(
            "IS_EMRI_AKTIF_KAYIT_MEVCUT", "Tahmin için aktif iş emri zaten mevcut."
        ) from exc


def _locked(order_id, expected_version):
    order = BakimIsEmri.objects.select_for_update().filter(pk=order_id).first()
    if not order:
        raise NotFound("İş emri bulunamadı.")
    if order.version != expected_version:
        raise EszamanliGuncellemeHatasi()
    return order


def is_emri_ata(*, order_id, actor, trace_id, expected_version, assignee, note=None):
    if actor.rol != Kullanici.Rol.ADMIN:
        raise PermissionDenied("Atama için yönetici yetkisi gereklidir.")
    if not assignee.is_active or assignee.rol not in {
        Kullanici.Rol.USER,
        Kullanici.Rol.ADMIN,
    }:
        raise IsEmriGecisiHatasi("Atanan kullanıcı aktif USER veya ADMIN olmalıdır.")
    with transaction.atomic():
        order = _locked(order_id, expected_version)
        if order.durum not in {"ACIK", "ATANDI", "BEKLEMEDE"}:
            raise IsEmriGecisiHatasi()
        old_state, old_assignee = order.durum, order.atanan_kullanici
        order.atanan_kullanici = assignee
        order.durum = "ATANDI"
        order.bekleme_nedeni = None
        order.version += 1
        order.save()
        _olay(
            order=order,
            actor=actor,
            trace_id=trace_id,
            event_type="ATANDI",
            old_state=old_state,
            description=note,
            old_assignee=old_assignee,
            new_assignee=assignee,
        )
        return order


def is_emri_durum_gecisi(*, order_id, actor, trace_id, expected_version, target, data):
    values = deepcopy(data)
    with transaction.atomic():
        order = _locked(order_id, expected_version)
        is_admin = actor.rol == Kullanici.Rol.ADMIN
        if not is_admin and order.atanan_kullanici_id != actor.id:
            raise PermissionDenied("Yalnız atanmış kullanıcı iş emrini değiştirebilir.")
        if target == "IPTAL_EDILDI" and not is_admin:
            raise PermissionDenied("İptal için yönetici yetkisi gereklidir.")
        try:
            gecisi_dogrula(
                mevcut_durum=order.durum,
                hedef_durum=target,
                atanan_var=bool(order.atanan_kullanici_id),
                veriler=values,
            )
        except IsEmriPolitikaHatasi as exc:
            raise IsEmriGecisiHatasi(str(exc)) from exc
        old_state = order.durum
        now = timezone.now()
        order.durum = target
        if target == "DEVAM_EDIYOR":
            order.gercek_baslangic_zamani = order.gercek_baslangic_zamani or now
            order.bekleme_nedeni = None
        elif target == "BEKLEMEDE":
            order.bekleme_nedeni = values["bekleme_nedeni"].strip()
        elif target == "TAMAMLANDI":
            order.tamamlama_notu = values["tamamlama_notu"].strip()
            order.tamamlanma_zamani = now
        elif target == "IPTAL_EDILDI":
            order.iptal_nedeni = values["iptal_nedeni"].strip()
            order.iptal_zamani = now
        order.version += 1
        order.save()
        event_type = {
            "BEKLEMEDE": "BEKLEMEYE_ALINDI",
            "DEVAM_EDIYOR": "DEVAM_ETTIRILDI",
            "TAMAMLANDI": "TAMAMLANDI",
            "IPTAL_EDILDI": "IPTAL_EDILDI",
        }.get(target, "DURUM_DEGISTI")
        description = (
            values.get("neden")
            or values.get("bekleme_nedeni")
            or values.get("tamamlama_notu")
            or values.get("iptal_nedeni")
        )
        _olay(
            order=order,
            actor=actor,
            trace_id=trace_id,
            event_type=event_type,
            old_state=old_state,
            description=description,
            old_assignee=order.atanan_kullanici,
            new_assignee=order.atanan_kullanici,
        )
        return order


def is_emri_oncelik_override(
    *,
    order_id,
    actor,
    trace_id,
    expected_version,
    priority=None,
    general_priority=None,
    reason,
):
    if actor.rol != Kullanici.Rol.ADMIN:
        raise PermissionDenied("Öncelik değişikliği için yönetici yetkisi gereklidir.")
    with transaction.atomic():
        order = _locked(order_id, expected_version)
        if order.durum in {"TAMAMLANDI", "IPTAL_EDILDI"}:
            raise IsEmriGecisiHatasi("Terminal iş emri değiştirilemez.")
        priority_type = _is_emri_oncelik_turu(order)
        if priority is not None and general_priority is not None:
            raise IsEmriCakismasiHatasi(
                "IS_EMRI_OVERRIDE_ISTEGI_BELIRSIZ",
                "Genel ve legacy öncelik alanları birlikte gönderilemez.",
            )
        if priority is None and general_priority is None:
            raise IsEmriCakismasiHatasi(
                "IS_EMRI_OVERRIDE_ONCELIGI_EKSIK",
                "Override için bir öncelik değeri gereklidir.",
            )
        now = timezone.now()
        if priority_type == "canonical":
            if general_priority is None:
                raise IsEmriCakismasiHatasi(
                    "IS_EMRI_CANONICAL_OVERRIDE_ALANI_GECERSIZ",
                    "Canonical iş emirlerinde 1–5 genel öncelik kullanılmalıdır.",
                )
            old_general_priority = order.etkin_genel_oncelik
            if old_general_priority == general_priority:
                raise IsEmriGecisiHatasi("Aynı öncelik yeniden uygulanamaz.")
            try:
                deadline = genel_oncelik_hedef_mudahale_zamani(
                    baslangic=now, genel_oncelik=general_priority
                )
            except IsEmriPolitikaHatasi as exc:
                raise IsEmriCakismasiHatasi(
                    "IS_EMRI_CANONICAL_SLA_GECERSIZ",
                    "İş emri genel öncelik SLA bilgisi geçersizdir.",
                ) from exc
            order.etkin_genel_oncelik = general_priority
            old_priority = new_priority = None
            new_general_priority = general_priority
        else:
            if priority is None:
                raise IsEmriCakismasiHatasi(
                    "IS_EMRI_LEGACY_OVERRIDE_ALANI_GECERSIZ",
                    "Legacy iş emirlerinde dört seviyeli öncelik kullanılmalıdır.",
                )
            old_priority = order.etkin_oncelik_seviyesi
            if old_priority == priority:
                raise IsEmriGecisiHatasi("Aynı öncelik yeniden uygulanamaz.")
            deadline = hedef_mudahale_zamani(baslangic=now, oncelik=priority)
            order.etkin_oncelik_seviyesi = priority
            new_priority = priority
            old_general_priority = new_general_priority = None
        order.manuel_oncelik_override = True
        order.override_nedeni = reason.strip()
        order.hedef_mudahale_zamani = deadline
        order.version += 1
        order.save()
        _olay(
            order=order,
            actor=actor,
            trace_id=trace_id,
            event_type="ONCELIK_OVERRIDE_EDILDI",
            old_state=order.durum,
            description=reason,
            old_priority=old_priority,
            new_priority=new_priority,
            old_general_priority=old_general_priority,
            new_general_priority=new_general_priority,
        )
        return order
