import math
import re

from bakim_ml.data_contract import ALLOWED_PRODUCT_TYPES
from django.utils import timezone
from rest_framework import serializers

from apps.tahminler.models import (
    ArizaTipiSnapshot,
    ErpSnapshot,
    ShapEtkisiSnapshot,
    TahminKaydi,
)


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

    def validate_hava_sicakligi_k(self, value):
        if value <= 0:
            raise serializers.ValidationError("Hava sıcaklığı 0 K'den büyük olmalıdır.")
        return value

    def validate_proses_sicakligi_k(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Proses sıcaklığı 0 K'den büyük olmalıdır."
            )
        return value

    def validate_donus_hizi_rpm(self, value):
        if value <= 0:
            raise serializers.ValidationError("Dönüş hızı sıfırdan büyük olmalıdır.")
        return value


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


class TahminKaydiFiltreSerializer(serializers.Serializer):
    makine_id = serializers.IntegerField(required=False, min_value=1)
    risk_uyarisi = serializers.BooleanField(required=False)
    kaynak = serializers.ChoiceField(required=False, choices=TahminKaydi.Kaynak.choices)
    olcum_zamani_baslangic = serializers.DateTimeField(required=False)
    olcum_zamani_bitis = serializers.DateTimeField(required=False)
    ariza_tipi = serializers.ChoiceField(
        required=False, choices=ArizaTipiSnapshot.Kod.choices
    )

    def validate(self, attrs):
        start = attrs.get("olcum_zamani_baslangic")
        end = attrs.get("olcum_zamani_bitis")
        if start and end and start > end:
            raise serializers.ValidationError("Baslangic bitisten sonra olamaz.")
        return attrs


class ShapEtkisiSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShapEtkisiSnapshot
        exclude = ("tahmin", "ariza_tipi")


class ArizaTipiSerializer(serializers.ModelSerializer):
    shap_etkileri = ShapEtkisiSerializer(many=True)

    class Meta:
        model = ArizaTipiSnapshot
        exclude = ("tahmin",)


class ErpSnapshotSerializer(serializers.ModelSerializer):
    ariza_tipi = serializers.CharField(source="ariza_tipi.kod")

    class Meta:
        model = ErpSnapshot
        exclude = ("tahmin", "parca")


class TahminKaydiListeSerializer(serializers.ModelSerializer):
    makine = serializers.SerializerMethodField()
    olusturan = serializers.SerializerMethodField()
    en_yuksek_guvenilir_ariza_tipi = serializers.SerializerMethodField()
    erp_snapshot_var = serializers.SerializerMethodField()

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


class TahminKaydiDetaySerializer(serializers.ModelSerializer):
    tekrarlandi = serializers.SerializerMethodField()
    makine = serializers.SerializerMethodField()
    olusturan = serializers.SerializerMethodField()
    tahmin = serializers.SerializerMethodField()
    ariza_tipleri = ArizaTipiSerializer(many=True)
    shap_etkileri = serializers.SerializerMethodField()
    erp_snapshotlari = ErpSnapshotSerializer(many=True)

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
            "base_value": obj.binary_base_value,
        }

    def get_shap_etkileri(self, obj):
        return ShapEtkisiSerializer(obj.root_shap_etkileri, many=True).data
