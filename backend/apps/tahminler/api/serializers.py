import math

from bakim_ml.data_contract import ALLOWED_PRODUCT_TYPES
from rest_framework import serializers


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
