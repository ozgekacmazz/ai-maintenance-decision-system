import math
import re

from bakim_ml.data_contract import ALLOWED_PRODUCT_TYPES
from django.utils import timezone
from rest_framework import serializers
from rest_framework.fields import empty

from apps.tahminler.domain_validation import model_girdilerini_dogrula
from apps.tahminler.models import (
    ArizaTipiSnapshot,
    BakimKarariSnapshot,
    ErpSnapshot,
    ShapEtkisiSnapshot,
    TahminKaydi,
    TahminReddi,
)
from apps.tahminler.selectors import secilen_is_emri


class SonluSayiAlani(serializers.FloatField):
    default_error_messages = {
        "invalid": "Geçerli bir sayı girin.",
        "not_finite": "NaN veya sonsuz değer kabul edilmez.",
    }

    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail("invalid")
        value = super().to_internal_value(data)
        if not math.isfinite(value):
            self.fail("not_finite")
        return value


class RiskTahminiGirdiSerializer(serializers.Serializer):
    urun_tipi = serializers.ChoiceField(
        choices=sorted(ALLOWED_PRODUCT_TYPES),
        error_messages={"invalid_choice": "Ürün tipi L, M veya H olmalıdır."},
    )
    hava_sicakligi_k = SonluSayiAlani(
        min_value=0,
        error_messages={"min_value": "Hava sıcaklığı 0 K'den büyük olmalıdır."},
    )
    proses_sicakligi_k = SonluSayiAlani(
        min_value=0,
        error_messages={"min_value": "Proses sıcaklığı 0 K'den büyük olmalıdır."},
    )
    donus_hizi_rpm = SonluSayiAlani(
        min_value=0,
        error_messages={"min_value": "Dönüş hızı sıfırdan büyük olmalıdır."},
    )
    tork_nm = SonluSayiAlani(
        min_value=0, error_messages={"min_value": "Tork negatif olamaz."}
    )
    takim_asinmasi_dk = SonluSayiAlani(
        min_value=0, error_messages={"min_value": "Takım aşınması negatif olamaz."}
    )

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("JSON nesnesi gönderilmelidir.")
        unexpected = sorted(set(data) - set(self.fields))
        if unexpected:
            raise serializers.ValidationError(
                {field: ["Beklenmeyen alan."] for field in unexpected}
            )
        return super().to_internal_value(data)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return model_girdilerini_dogrula(attrs)


class TahminReddetSerializer(serializers.Serializer):
    red_nedeni = serializers.CharField(required=False, allow_blank=True, max_length=500)


class TahminKaydiYazmaSerializer(serializers.Serializer):
    makine_id = serializers.IntegerField(min_value=1)
    olcum_zamani = serializers.DateTimeField()
    kaynak = serializers.ChoiceField(choices=TahminKaydi.Kaynak.choices)
    idempotency_key = serializers.CharField(max_length=128, trim_whitespace=False)
    sensor_verisi = RiskTahminiGirdiSerializer()

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("JSON nesnesi gonderilmelidir.")
        unexpected = sorted(set(data) - set(self.fields))
        if unexpected:
            raise serializers.ValidationError(
                {field: ["Beklenmeyen alan."] for field in unexpected}
            )
        return super().to_internal_value(data)

    def validate_idempotency_key(self, value):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value):
            raise serializers.ValidationError("Gecersiz idempotency anahtari.")
        return value

    def validate_olcum_zamani(self, value):
        if timezone.is_naive(value):
            raise serializers.ValidationError("Timezone bilgisi zorunludur.")
        if value > timezone.now() + timezone.timedelta(minutes=5):
            raise serializers.ValidationError(
                "Olcum zamani en fazla 5 dakika ileride olabilir."
            )
        return value


class SorguBooleanField(serializers.BooleanField):
    default_empty_html = empty


class TahminKaydiFiltreSerializer(serializers.Serializer):
    makine_id = serializers.IntegerField(required=False, min_value=1)
    genel_oncelik = serializers.IntegerField(required=False, min_value=1, max_value=5)
    risk_uyarisi = SorguBooleanField(required=False)
    kaynak = serializers.ChoiceField(required=False, choices=TahminKaydi.Kaynak.choices)
    olcum_zamani_baslangic = serializers.DateTimeField(required=False)
    olcum_zamani_bitis = serializers.DateTimeField(required=False)
    ariza_tipi = serializers.ChoiceField(
        required=False, choices=ArizaTipiSnapshot.Kod.choices
    )
    oncelik_seviyesi = serializers.ChoiceField(
        required=False, choices=BakimKarariSnapshot.OncelikSeviyesi.choices
    )
    ana_aksiyon = serializers.ChoiceField(
        required=False, choices=BakimKarariSnapshot.Aksiyon.choices
    )
    karar_guveni = serializers.ChoiceField(
        required=False, choices=BakimKarariSnapshot.KararGuveni.choices
    )
    minimum_nihai_skor = serializers.FloatField(
        required=False, min_value=0, max_value=100
    )
    maksimum_nihai_skor = serializers.FloatField(
        required=False, min_value=0, max_value=100
    )
    sirala = serializers.ChoiceField(
        required=False,
        choices=(
            "nihai_oncelik",
            "-nihai_oncelik",
            "genel_oncelik",
            "-genel_oncelik",
            "olcum_zamani",
            "-olcum_zamani",
            "risk_orani",
            "-risk_orani",
            "makine_kritiklik",
            "-makine_kritiklik",
        ),
    )

    def to_internal_value(self, data):
        unexpected = sorted(set(data) - set(self.fields) - {"sayfa", "sayfa_boyutu"})
        if unexpected:
            raise serializers.ValidationError(
                {field: ["Beklenmeyen filtre alanı."] for field in unexpected}
            )
        if "genel_oncelik" in data and data.get("genel_oncelik") == "":
            raise serializers.ValidationError(
                {"genel_oncelik": ["Bu alan boş bırakılamaz."]}
            )
        return super().to_internal_value(data)

    def validate(self, attrs):
        start = attrs.get("olcum_zamani_baslangic")
        end = attrs.get("olcum_zamani_bitis")
        if start and end and start > end:
            raise serializers.ValidationError("Baslangic bitisten sonra olamaz.")
        minimum = attrs.get("minimum_nihai_skor")
        maximum = attrs.get("maksimum_nihai_skor")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise serializers.ValidationError(
                "Minimum nihai skor maksimumdan büyük olamaz."
            )
        return attrs


class TahminLoguFiltreSerializer(serializers.Serializer):
    karar_durumu = serializers.ChoiceField(
        required=False, choices=("BEKLIYOR", "ONAYLANDI", "REDDEDILDI", "TUTARSIZ")
    )
    makine_id = serializers.IntegerField(required=False, min_value=1)
    makine_kodu = serializers.CharField(required=False, max_length=50)
    kaynak = serializers.ChoiceField(required=False, choices=TahminKaydi.Kaynak.choices)
    baslangic = serializers.DateField(required=False)
    bitis = serializers.DateField(required=False)
    genel_oncelik = serializers.IntegerField(required=False, min_value=1, max_value=5)
    sirala = serializers.ChoiceField(
        required=False,
        choices=(
            "olcum_zamani",
            "-olcum_zamani",
            "risk_orani",
            "-risk_orani",
            "genel_oncelik",
            "-genel_oncelik",
            "karar_zamani",
            "-karar_zamani",
        ),
    )

    def to_internal_value(self, data):
        unexpected = sorted(set(data) - set(self.fields) - {"sayfa", "sayfa_boyutu"})
        if unexpected:
            raise serializers.ValidationError(
                {field: ["Beklenmeyen filtre alanı."] for field in unexpected}
            )
        return super().to_internal_value(data)

    def validate(self, attrs):
        if (
            attrs.get("baslangic")
            and attrs.get("bitis")
            and attrs["baslangic"] > attrs["bitis"]
        ):
            raise serializers.ValidationError(
                {"bitis": ["Bitiş tarihi başlangıç tarihinden önce olamaz."]}
            )
        return attrs


class ShapEtkisiSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShapEtkisiSnapshot
        exclude = ("tahmin", "ariza_tipi")


class ArizaTipiSerializer(serializers.ModelSerializer):
    shap_etkileri = serializers.SerializerMethodField()

    class Meta:
        model = ArizaTipiSnapshot
        exclude = ("tahmin",)

    def get_shap_etkileri(self, obj):
        items = self.context.get("shap_by_failure", {}).get(obj.pk, ())
        return ShapEtkisiSerializer(items, many=True).data


class ErpSnapshotSerializer(serializers.ModelSerializer):
    ariza_tipi = serializers.CharField(source="ariza_tipi.kod")

    class Meta:
        model = ErpSnapshot
        exclude = ("tahmin", "parca")


class KararGerekcesiSerializer(serializers.Serializer):
    kod = serializers.CharField()
    mesaj = serializers.CharField(source="mesaj_snapshot")
    etki = serializers.CharField()
    puan_etkisi = serializers.FloatField(allow_null=True)


class KararUyarisiSerializer(serializers.Serializer):
    kod = serializers.CharField()
    mesaj = serializers.CharField(source="mesaj_snapshot")


class BakimKarariSerializer(serializers.ModelSerializer):
    gerekceler = KararGerekcesiSerializer(many=True)
    destekleyici_aksiyonlar = serializers.SerializerMethodField()
    uyarilar = KararUyarisiSerializer(many=True)

    class Meta:
        model = BakimKarariSnapshot
        fields = (
            "motor_surumu",
            "teknik_aciliyet_skoru",
            "tedarik_riski_skoru",
            "nihai_oncelik_skoru",
            "oncelik_seviyesi",
            "genel_oncelik",
            "stok_katsayisi",
            "ham_genel_oncelik",
            "genel_oncelik_formul_surumu",
            "ana_aksiyon",
            "destekleyici_aksiyonlar",
            "ana_ariza_tipi",
            "karar_guveni",
            "gerekceler",
            "uyarilar",
            "olusturulma_zamani",
        )

    def get_destekleyici_aksiyonlar(self, obj):
        return [item.aksiyon for item in obj.destekleyici_aksiyonlar.all()]


class TahminKaydiListeSerializer(serializers.ModelSerializer):
    makine = serializers.SerializerMethodField()
    olusturan = serializers.SerializerMethodField()
    en_yuksek_guvenilir_ariza_tipi = serializers.SerializerMethodField()
    erp_snapshot_var = serializers.SerializerMethodField()
    nihai_oncelik_skoru = serializers.SerializerMethodField()
    oncelik_seviyesi = serializers.SerializerMethodField()
    genel_oncelik = serializers.SerializerMethodField()
    genel_oncelik_formul_surumu = serializers.SerializerMethodField()
    ana_aksiyon = serializers.SerializerMethodField()
    karar_guveni = serializers.SerializerMethodField()

    class Meta:
        model = TahminKaydi
        fields = (
            "id",
            "makine",
            "olcum_zamani",
            "risk_orani",
            "risk_uyarisi",
            "en_yuksek_guvenilir_ariza_tipi",
            "belirsiz_fiziksel_tip",
            "kaynak",
            "olusturan",
            "trace_id",
            "erp_snapshot_var",
            "nihai_oncelik_skoru",
            "oncelik_seviyesi",
            "genel_oncelik",
            "genel_oncelik_formul_surumu",
            "ana_aksiyon",
            "karar_guveni",
        )

    def get_makine(self, obj):
        return {
            "id": obj.makine_id,
            "kod": obj.makine_kodu_snapshot,
            "ad": obj.makine_adi_snapshot,
        }

    def get_olusturan(self, obj):
        return {"id": obj.olusturan_id, "kullanici_adi": obj.olusturan.username}

    def get_en_yuksek_guvenilir_ariza_tipi(self, obj):
        items = getattr(obj, "guvenilir_tipler", ())
        return items[0].kod if items else None

    def get_erp_snapshot_var(self, obj):
        return obj.erp_snapshot_var

    def _decision(self, obj):
        try:
            return obj.bakim_karari
        except BakimKarariSnapshot.DoesNotExist:
            return None

    def get_nihai_oncelik_skoru(self, obj):
        decision = self._decision(obj)
        return decision.nihai_oncelik_skoru if decision else None

    def get_oncelik_seviyesi(self, obj):
        decision = self._decision(obj)
        return decision.oncelik_seviyesi if decision else None

    def get_genel_oncelik(self, obj):
        decision = self._decision(obj)
        return decision.genel_oncelik if decision else None

    def get_genel_oncelik_formul_surumu(self, obj):
        decision = self._decision(obj)
        return decision.genel_oncelik_formul_surumu if decision else None

    def get_ana_aksiyon(self, obj):
        decision = self._decision(obj)
        return decision.ana_aksiyon if decision else None

    def get_karar_guveni(self, obj):
        decision = self._decision(obj)
        return decision.karar_guveni if decision else None


class TahminLoguSerializer(serializers.ModelSerializer):
    makine = serializers.SerializerMethodField()
    genel_oncelik = serializers.SerializerMethodField()
    legacy_oncelik_seviyesi = serializers.SerializerMethodField()
    legacy_nihai_oncelik_skoru = serializers.SerializerMethodField()
    karar_durumu = serializers.SerializerMethodField()
    karar_veren = serializers.SerializerMethodField()
    karar_zamani = serializers.SerializerMethodField()
    karar_nedeni = serializers.SerializerMethodField()
    is_emri_bilgisi = serializers.SerializerMethodField()
    onay_bilgisi = serializers.SerializerMethodField()
    red_bilgisi = serializers.SerializerMethodField()

    class Meta:
        model = TahminKaydi
        fields = (
            "id",
            "olcum_zamani",
            "makine",
            "kaynak",
            "risk_orani",
            "risk_uyarisi",
            "genel_oncelik",
            "legacy_oncelik_seviyesi",
            "legacy_nihai_oncelik_skoru",
            "karar_durumu",
            "karar_veren",
            "karar_zamani",
            "karar_nedeni",
            "is_emri_bilgisi",
            "onay_bilgisi",
            "red_bilgisi",
        )

    @staticmethod
    def _decision(obj):
        try:
            return obj.bakim_karari
        except BakimKarariSnapshot.DoesNotExist:
            return None

    @staticmethod
    def _red(obj):
        try:
            return obj.red_bilgisi
        except TahminReddi.DoesNotExist:
            return None

    def get_makine(self, obj):
        return {
            "id": obj.makine_id,
            "kod": obj.makine_kodu_snapshot,
            "ad": obj.makine_adi_snapshot,
        }

    def get_genel_oncelik(self, obj):
        decision = self._decision(obj)
        return decision.genel_oncelik if decision else None

    def get_legacy_oncelik_seviyesi(self, obj):
        decision = self._decision(obj)
        return decision.oncelik_seviyesi if decision else None

    def get_legacy_nihai_oncelik_skoru(self, obj):
        decision = self._decision(obj)
        return decision.nihai_oncelik_skoru if decision else None

    def get_karar_durumu(self, obj):
        has_order = bool(obj.log_is_emri_var)
        has_red = bool(obj.log_red_var)
        if has_order and has_red:
            return "TUTARSIZ"
        if has_order:
            return "ONAYLANDI"
        if has_red:
            return "REDDEDILDI"
        return "BEKLIYOR"

    def get_karar_veren(self, obj):
        status = self.get_karar_durumu(obj)
        if status == "ONAYLANDI":
            order = secilen_is_emri(obj)
            return order.olusturan.username if order else None
        if status == "REDDEDILDI":
            red = self._red(obj)
            return red.reddeden.username if red else None
        return None

    def get_karar_zamani(self, obj):
        status = self.get_karar_durumu(obj)
        if status == "ONAYLANDI":
            order = secilen_is_emri(obj)
            return order.olusturulma_zamani if order else None
        if status == "REDDEDILDI":
            red = self._red(obj)
            return red.olusturulma_zamani if red else None
        return None

    def get_karar_nedeni(self, obj):
        red = self._red(obj)
        return (
            red.red_nedeni
            if self.get_karar_durumu(obj) == "REDDEDILDI" and red
            else None
        )

    def get_is_emri_bilgisi(self, obj):
        return (
            self.get_onay_bilgisi(obj)
            if self.get_karar_durumu(obj) == "ONAYLANDI"
            else None
        )

    def get_onay_bilgisi(self, obj):
        order = secilen_is_emri(obj)
        if not order:
            return None
        return {
            "id": str(order.id),
            "is_emri_numarasi": order.is_emri_numarasi,
            "durum": order.durum,
            "olusturan": order.olusturan.username,
            "olusturulma_zamani": serializers.DateTimeField().to_representation(
                order.olusturulma_zamani
            ),
        }

    def get_red_bilgisi(self, obj):
        red = self._red(obj)
        if not red:
            return None
        return {
            "reddeden": red.reddeden.username,
            "reddetme_zamani": red.olusturulma_zamani,
            "red_nedeni": red.red_nedeni,
        }


class TahminKaydiDetaySerializer(serializers.ModelSerializer):
    tekrarlandi = serializers.SerializerMethodField()
    makine = serializers.SerializerMethodField()
    olusturan = serializers.SerializerMethodField()
    tahmin = serializers.SerializerMethodField()
    ariza_tipleri = serializers.SerializerMethodField()
    shap_etkileri = serializers.SerializerMethodField()
    erp_snapshotlari = ErpSnapshotSerializer(many=True)
    bakim_karari = serializers.SerializerMethodField()

    red_bilgisi = serializers.SerializerMethodField()
    is_emri_bilgisi = serializers.SerializerMethodField()

    class Meta:
        model = TahminKaydi
        fields = (
            "id",
            "tekrarlandi",
            "makine",
            "olcum_zamani",
            "olusturulma_zamani",
            "kaynak",
            "sensor_snapshot",
            "tahmin",
            "failure_type_durum",
            "failure_type_model_version",
            "failure_type_pipeline_version",
            "belirsiz_fiziksel_tip",
            "aciklanabilirlik_durum",
            "ariza_tipleri",
            "shap_etkileri",
            "erp_snapshotlari",
            "olusturan",
            "trace_id",
            "bakim_karari",
            "red_bilgisi",
            "is_emri_bilgisi",
        )

    def get_tekrarlandi(self, obj):
        return bool(self.context.get("tekrarlandi", False))

    def get_makine(self, obj):
        return {
            "id": obj.makine_id,
            "kod": obj.makine_kodu_snapshot,
            "ad": obj.makine_adi_snapshot,
            "kritiklik_snapshot": obj.kritiklik_snapshot,
        }

    def get_olusturan(self, obj):
        return {"id": obj.olusturan_id, "kullanici_adi": obj.olusturan.username}

    def get_tahmin(self, obj):
        return {
            "risk_orani": obj.risk_orani,
            "risk_uyarisi": obj.risk_uyarisi,
            "threshold": obj.binary_threshold,
            "model_version": obj.binary_model_version,
            "pipeline_version": obj.binary_pipeline_version,
            "input_domain_contract_surumu": obj.input_domain_contract_surumu,
            "base_value": obj.binary_base_value,
        }

    def get_shap_etkileri(self, obj):
        return ShapEtkisiSerializer(
            [item for item in obj.tum_shap_etkileri if item.ariza_tipi_id is None],
            many=True,
        ).data

    def get_ariza_tipleri(self, obj):
        by_failure = {}
        for item in obj.tum_shap_etkileri:
            if item.ariza_tipi_id is not None:
                by_failure.setdefault(item.ariza_tipi_id, []).append(item)
        return ArizaTipiSerializer(
            obj.ariza_tipleri.all(),
            many=True,
            context={"shap_by_failure": by_failure},
        ).data

    def get_bakim_karari(self, obj):
        try:
            decision = obj.bakim_karari
        except BakimKarariSnapshot.DoesNotExist:
            return None
        return BakimKarariSerializer(decision).data

    def get_red_bilgisi(self, obj):
        try:
            red = obj.red_bilgisi
            return {
                "reddeden": red.reddeden.username,
                "reddetme_zamani": red.olusturulma_zamani,
                "red_nedeni": red.red_nedeni,
            }
        except Exception:
            return None

    def get_is_emri_bilgisi(self, obj):
        is_emri = secilen_is_emri(obj)
        if not is_emri:
            return None
        return {
            "id": str(is_emri.id),
            "is_emri_numarasi": is_emri.is_emri_numarasi,
            "durum": is_emri.durum,
            "olusturan": is_emri.olusturan.username,
            "olusturulma_zamani": serializers.DateTimeField().to_representation(
                is_emri.olusturulma_zamani
            ),
        }
