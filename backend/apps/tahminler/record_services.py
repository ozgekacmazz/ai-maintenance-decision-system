import hashlib
import json
from datetime import timezone as datetime_timezone

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from apps.bakim.models import ArizaParcaKurali, Makine
from apps.tahminler.decision_engine import bakim_karari_hesapla
from apps.tahminler.exceptions import IdempotencyCakismasiHatasi, KararMotoruHatasi
from apps.tahminler.genel_oncelik import genel_oncelik_hesapla
from apps.tahminler.models import (
    ArizaTipiSnapshot,
    BakimKarariSnapshot,
    ErpSnapshot,
    KararAksiyonuSnapshot,
    KararGerekcesiSnapshot,
    KararUyarisiSnapshot,
    ShapEtkisiSnapshot,
    TahminKaydi,
)
from apps.tahminler.services import _ozellikleri_hazirla, hiyerarsik_risk_tahmini_yap


def payload_fingerprint(*, makine_id, olcum_zamani, kaynak, sensor_verisi):
    def canonical_number(value):
        if isinstance(value, float) and value == 0:
            return 0.0
        return value

    document = {
        "makine_id": int(makine_id),
        "olcum_zamani": olcum_zamani.astimezone(datetime_timezone.utc).isoformat(),
        "kaynak": kaynak,
        "sensor_verisi": {
            key: canonical_number(value) for key, value in dict(sensor_verisi).items()
        },
    }
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mevcut_kaydi_kontrol_et(*, makine_id, kaynak, idempotency_key, fingerprint):
    existing = TahminKaydi.objects.filter(
        makine_id=makine_id, kaynak=kaynak, idempotency_key=idempotency_key
    ).first()
    if existing is None:
        return None
    if existing.payload_fingerprint != fingerprint:
        raise IdempotencyCakismasiHatasi
    return existing


def _shap_kaydet(*, tahmin, explanation, ariza_tipi=None):
    if not explanation:
        return
    for index, effect in enumerate(explanation["ilk_etkiler"], start=1):
        ShapEtkisiSnapshot.objects.create(
            tahmin=tahmin,
            ariza_tipi=ariza_tipi,
            hedef=explanation["target"],
            sira=index,
            feature=effect["feature"],
            gorunen_ad=effect["gorunen_ad"],
            original_feature_value=effect["original_feature_value"],
            model_feature_value=effect["model_feature_value"],
            birim=effect["birim"],
            shap_value=effect["shap_value"],
            yon=effect["yon"],
        )


def _ariza_ve_erp_kaydet(*, tahmin, evaluation):
    failure_snapshots = []
    erp_snapshots = []
    items = [
        (item, True, index)
        for index, item in enumerate(evaluation["guvenilir_adaylar"], start=1)
    ]
    items.extend((item, False, None) for item in evaluation["deneysel_sinyaller"])
    for item, trusted, order in items:
        label = item["kod"]
        explanation = item.get("aciklama")
        snapshot = ArizaTipiSnapshot.objects.create(
            tahmin=tahmin,
            kod=label,
            olasilik=item["olasilik"],
            threshold=item["threshold"],
            esik_asildi=item.get("esik_asildi", True),
            guven_durumu=item.get("guven_durumu"),
            operasyonel_kullanima_uygun=item.get(
                "operasyonel_kullanima_uygun", trusted
            ),
            guvenilir_aday=trusted,
            siralama=order,
            base_value=explanation["base_value"] if explanation else None,
        )
        failure_snapshots.append(snapshot)
        _shap_kaydet(tahmin=tahmin, explanation=explanation, ariza_tipi=snapshot)
        if not snapshot.esik_asildi:
            continue
        rules = (
            ArizaParcaKurali.objects.select_related("parca__stok")
            .filter(
                ariza_tipi=label, aktif=True, parca__isnull=False, parca__aktif=True
            )
            .order_by("tercih_sirasi", "parca__parca_kodu", "id")
        )
        for rule in rules:
            try:
                stock = rule.parca.stok
            except ObjectDoesNotExist:
                stock_status = ErpSnapshot.StokDurumu.KAYIT_YOK
                total = minimum = lead_days = None
            else:
                stock_status = ErpSnapshot.StokDurumu.MEVCUT
                total = stock.adet
                minimum = stock.minimum_stok
                lead_days = stock.tedarik_gun
            erp_snapshots.append(
                ErpSnapshot.objects.create(
                    tahmin=tahmin,
                    ariza_tipi=snapshot,
                    parca=rule.parca,
                    parca_kodu_snapshot=rule.parca.parca_kodu,
                    parca_adi_snapshot=rule.parca.ad,
                    gerekli_miktar=rule.gerekli_miktar,
                    stok_durumu=stock_status,
                    toplam_stok=total,
                    kullanilabilir_stok=total,
                    minimum_stok=minimum,
                    tedarik_gun=lead_days,
                    stok_yeterli=(
                        total >= rule.gerekli_miktar if total is not None else False
                    ),
                    deneysel=not trusted,
                    onerilen_aksiyon_snapshot=rule.onerilen_aksiyon,
                )
            )
    return failure_snapshots, erp_snapshots


def _karar_kaydet(*, tahmin, failure_snapshots, erp_snapshots):
    engine_input = {
        "risk_orani": tahmin.risk_orani,
        "risk_uyarisi": tahmin.risk_uyarisi,
        "kritiklik_snapshot": tahmin.kritiklik_snapshot,
        "belirsiz_fiziksel_tip": tahmin.belirsiz_fiziksel_tip,
        "ariza_tipleri": [
            {
                "kod": item.kod,
                "esik_asildi": item.esik_asildi,
                "operasyonel_kullanima_uygun": item.operasyonel_kullanima_uygun,
                "guvenilir_aday": item.guvenilir_aday,
                "siralama": item.siralama,
            }
            for item in failure_snapshots
        ],
        "erp_snapshotlari": [
            {
                "parca_kodu_snapshot": item.parca_kodu_snapshot,
                "gerekli_miktar": item.gerekli_miktar,
                "stok_durumu": item.stok_durumu,
                "kullanilabilir_stok": item.kullanilabilir_stok,
                "minimum_stok": item.minimum_stok,
                "tedarik_gun": item.tedarik_gun,
                "stok_yeterli": item.stok_yeterli,
            }
            for item in erp_snapshots
            if not item.deneysel
        ],
    }
    try:
        result = bakim_karari_hesapla(engine_input)
        canonical_result = genel_oncelik_hesapla(
            risk_orani=tahmin.risk_orani,
            makine_kritikligi=tahmin.kritiklik_snapshot,
            tedarik_riski_skoru=result["tedarik_riski_skoru"],
        )
    except Exception as exc:
        raise KararMotoruHatasi() from exc
    decision = BakimKarariSnapshot.objects.create(
        tahmin=tahmin,
        motor_surumu=result["motor_surumu"],
        teknik_aciliyet_skoru=result["teknik_aciliyet_skoru"],
        tedarik_riski_skoru=result["tedarik_riski_skoru"],
        nihai_oncelik_skoru=result["nihai_oncelik_skoru"],
        oncelik_seviyesi=result["oncelik_seviyesi"],
        genel_oncelik=canonical_result.genel_oncelik,
        stok_katsayisi=canonical_result.stok_katsayisi,
        ham_genel_oncelik=canonical_result.ham_genel_oncelik,
        genel_oncelik_formul_surumu=canonical_result.formul_surumu,
        ana_aksiyon=result["ana_aksiyon"],
        ana_ariza_tipi=result["ana_ariza_tipi"],
        karar_guveni=result["karar_guveni"],
    )
    for index, reason in enumerate(result["gerekceler"], start=1):
        KararGerekcesiSnapshot.objects.create(
            karar=decision,
            kod=reason["kod"],
            mesaj_snapshot=reason["mesaj"],
            etki=reason["etki"],
            puan_etkisi=reason["puan_etkisi"],
            sira=index,
        )
    for index, action in enumerate(result["destekleyici_aksiyonlar"], start=1):
        KararAksiyonuSnapshot.objects.create(karar=decision, aksiyon=action, sira=index)
    for index, warning in enumerate(result["uyarilar"], start=1):
        KararUyarisiSnapshot.objects.create(
            karar=decision,
            kod=warning["kod"],
            mesaj_snapshot=warning["mesaj"],
            sira=index,
        )
    return decision


def _kaydi_yaz(
    *,
    makine,
    kullanici,
    trace_id,
    kaynak,
    idempotency_key,
    fingerprint,
    olcum_zamani,
    sensor_verisi,
    features,
    result,
):
    features = features.iloc[0].to_dict()
    feature_snapshot = {
        key: value.item() if hasattr(value, "item") else value
        for key, value in features.items()
    }
    sensor_snapshot = {**sensor_verisi, **feature_snapshot}
    evaluation = result["ariza_tipi_degerlendirmesi"]
    explainability = result["aciklanabilirlik"]
    tahmin = TahminKaydi.objects.create(
        makine=makine,
        olusturan=kullanici,
        trace_id=trace_id,
        kaynak=kaynak,
        olcum_zamani=olcum_zamani,
        idempotency_key=idempotency_key,
        payload_fingerprint=fingerprint,
        makine_kodu_snapshot=makine.makine_kodu,
        makine_adi_snapshot=makine.ad,
        kritiklik_snapshot=makine.kritiklik,
        sensor_snapshot=sensor_snapshot,
        risk_orani=result["risk_orani"],
        risk_uyarisi=result["risk_uyarisi"],
        binary_threshold=result["threshold"],
        binary_model_version=result["model_version"],
        binary_pipeline_version=result["pipeline_version"],
        input_domain_contract_surumu=result.get("input_domain_contract_surumu"),
        failure_type_durum=evaluation["durum"],
        failure_type_model_version=evaluation.get("model_version"),
        failure_type_pipeline_version=evaluation.get("pipeline_version"),
        belirsiz_fiziksel_tip=evaluation["belirsiz_fiziksel_tip"],
        aciklanabilirlik_durum=explainability["durum"],
        binary_base_value=(
            explainability["risk_aciklamasi"]["base_value"]
            if explainability["risk_aciklamasi"]
            else None
        ),
    )
    _shap_kaydet(tahmin=tahmin, explanation=explainability["risk_aciklamasi"])
    failure_snapshots, erp_snapshots = _ariza_ve_erp_kaydet(
        tahmin=tahmin, evaluation=evaluation
    )
    _karar_kaydet(
        tahmin=tahmin,
        failure_snapshots=failure_snapshots,
        erp_snapshots=erp_snapshots,
    )
    return tahmin


def tahmin_kaydi_olustur(*, kullanici, trace_id, veriler):
    sensor_verisi = dict(veriler["sensor_verisi"])
    makine = get_object_or_404(
        Makine.objects.filter(aktif=True), pk=veriler["makine_id"]
    )
    fingerprint = payload_fingerprint(
        makine_id=makine.pk,
        olcum_zamani=veriler["olcum_zamani"],
        kaynak=veriler["kaynak"],
        sensor_verisi=sensor_verisi,
    )
    existing = _mevcut_kaydi_kontrol_et(
        makine_id=makine.pk,
        kaynak=veriler["kaynak"],
        idempotency_key=veriler["idempotency_key"],
        fingerprint=fingerprint,
    )
    if existing:
        return existing, True
    features = _ozellikleri_hazirla(sensor_verisi)
    result = hiyerarsik_risk_tahmini_yap(sensor_verisi, features=features)
    try:
        with transaction.atomic():
            locked_machine = get_object_or_404(
                Makine.objects.select_for_update().filter(aktif=True), pk=makine.pk
            )
            existing = _mevcut_kaydi_kontrol_et(
                makine_id=makine.pk,
                kaynak=veriler["kaynak"],
                idempotency_key=veriler["idempotency_key"],
                fingerprint=fingerprint,
            )
            if existing:
                return existing, True
            created = _kaydi_yaz(
                makine=locked_machine,
                kullanici=kullanici,
                trace_id=trace_id,
                kaynak=veriler["kaynak"],
                idempotency_key=veriler["idempotency_key"],
                fingerprint=fingerprint,
                olcum_zamani=veriler["olcum_zamani"],
                sensor_verisi=sensor_verisi,
                features=features,
                result=result,
            )
        return created, False
    except IntegrityError:
        existing = _mevcut_kaydi_kontrol_et(
            makine_id=makine.pk,
            kaynak=veriler["kaynak"],
            idempotency_key=veriler["idempotency_key"],
            fingerprint=fingerprint,
        )
        if existing is None:
            raise
        return existing, True
