from django.utils import timezone
from rest_framework import serializers
from rest_framework.fields import empty

from apps.bakim.models import BakimIsEmri, IsEmriOlayi
from apps.bakim.work_order_policy import gecikmis_mi
from apps.kullanicilar.models import Kullanici


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        unknown = sorted(set(data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {key: ["Beklenmeyen alan."] for key in unknown}
            )
        return super().to_internal_value(data)


class QueryBooleanField(serializers.BooleanField):
    default_empty_html = empty


def _text(value):
    value = value.strip()
    if not value:
        raise serializers.ValidationError("Bu alan boş olamaz.")
    return value


class IsEmriOlusturmaSerializer(StrictSerializer):
    tahmin_kaydi_id = serializers.UUIDField()
    idempotency_key = serializers.CharField(max_length=128)
    baslik = serializers.CharField(max_length=200)
    aciklama = serializers.CharField(max_length=2000)
    validate_idempotency_key = staticmethod(_text)
    validate_baslik = staticmethod(_text)
    validate_aciklama = staticmethod(_text)


class IsEmriAtamaSerializer(StrictSerializer):
    atanan_kullanici_id = serializers.PrimaryKeyRelatedField(
        source="atanan_kullanici", queryset=Kullanici.objects.all()
    )
    beklenen_version = serializers.IntegerField(min_value=1)
    not_ = serializers.CharField(required=False, max_length=500, allow_blank=False)

    def get_fields(self):
        fields = super().get_fields()
        fields["not"] = fields.pop("not_")
        return fields


class IsEmriDurumGecisiSerializer(StrictSerializer):
    beklenen_version = serializers.IntegerField(min_value=1)
    hedef_durum = serializers.ChoiceField(choices=BakimIsEmri.Durum.choices)
    neden = serializers.CharField(required=False, max_length=500, allow_blank=False)
    bekleme_nedeni = serializers.CharField(
        required=False, max_length=500, allow_blank=False
    )
    tamamlama_notu = serializers.CharField(
        required=False, max_length=2000, allow_blank=False
    )
    iptal_nedeni = serializers.CharField(
        required=False, max_length=500, allow_blank=False
    )

    def validate(self, attrs):
        relevant = {
            "BEKLEMEDE": "bekleme_nedeni",
            "TAMAMLANDI": "tamamlama_notu",
            "IPTAL_EDILDI": "iptal_nedeni",
        }.get(attrs["hedef_durum"])
        conditional = {"bekleme_nedeni", "tamamlama_notu", "iptal_nedeni"}
        supplied = conditional.intersection(attrs)
        if relevant and relevant not in supplied:
            raise serializers.ValidationError({relevant: ["Bu durum için zorunludur."]})
        unrelated = supplied - ({relevant} if relevant else set())
        if unrelated:
            raise serializers.ValidationError(
                {key: ["Hedef durumla ilgisiz alan."] for key in unrelated}
            )
        return attrs


class IsEmriOncelikOverrideSerializer(StrictSerializer):
    beklenen_version = serializers.IntegerField(min_value=1)
    etkin_oncelik_seviyesi = serializers.ChoiceField(
        choices=("DUSUK", "ORTA", "YUKSEK", "KRITIK")
    )
    override_nedeni = serializers.CharField(max_length=500)
    validate_override_nedeni = staticmethod(_text)


class IsEmriFiltreSerializer(StrictSerializer):
    durum = serializers.ChoiceField(required=False, choices=BakimIsEmri.Durum.choices)
    etkin_oncelik_seviyesi = serializers.ChoiceField(
        required=False, choices=("DUSUK", "ORTA", "YUKSEK", "KRITIK")
    )
    kaynak_oncelik_seviyesi = serializers.ChoiceField(
        required=False, choices=("DUSUK", "ORTA", "YUKSEK", "KRITIK")
    )
    makine_id = serializers.IntegerField(required=False, min_value=1)
    atanan_kullanici_id = serializers.IntegerField(required=False, min_value=1)
    olusturan_id = serializers.IntegerField(required=False, min_value=1)
    gecikmis = QueryBooleanField(required=False)
    manuel_oncelik_override = QueryBooleanField(required=False)
    olusturulma_baslangic = serializers.DateTimeField(required=False)
    olusturulma_bitis = serializers.DateTimeField(required=False)
    hedef_mudahale_baslangic = serializers.DateTimeField(required=False)
    hedef_mudahale_bitis = serializers.DateTimeField(required=False)
    ana_ariza_tipi = serializers.ChoiceField(
        required=False, choices=("HDF", "PWF", "OSF")
    )
    is_emri_numarasi = serializers.CharField(required=False, max_length=32)
    sirala = serializers.ChoiceField(
        required=False,
        choices=(
            "etkin_oncelik",
            "-etkin_oncelik",
            "hedef_mudahale_zamani",
            "-hedef_mudahale_zamani",
            "olusturulma_zamani",
            "-olusturulma_zamani",
            "guncellenme_zamani",
            "-guncellenme_zamani",
            "makine_kritiklik",
            "-makine_kritiklik",
            "kaynak_nihai_skor",
            "-kaynak_nihai_skor",
            "durum",
            "-durum",
        ),
    )
    sayfa = serializers.IntegerField(required=False, min_value=1, write_only=True)
    sayfa_boyutu = serializers.IntegerField(
        required=False, min_value=1, write_only=True
    )


class KullaniciOzetiSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kullanici_adi = serializers.CharField(source="username")


class IsEmriOlaySerializer(serializers.ModelSerializer):
    gerceklestiren_kullanici_adi = serializers.CharField(
        source="gerceklestiren_username_snapshot"
    )

    class Meta:
        model = IsEmriOlayi
        exclude = ("is_emri", "gerceklestiren")


class IsEmriListeSerializer(serializers.ModelSerializer):
    makine = serializers.SerializerMethodField()
    olusturan = KullaniciOzetiSerializer()
    atanan_kullanici = KullaniciOzetiSerializer(allow_null=True)
    gecikmis = serializers.SerializerMethodField()
    olcum_zamani = serializers.DateTimeField(source="tahmin_kaydi.olcum_zamani")

    class Meta:
        model = BakimIsEmri
        fields = (
            "id",
            "is_emri_numarasi",
            "makine",
            "durum",
            "etkin_oncelik_seviyesi",
            "kaynak_oncelik_seviyesi",
            "atanan_kullanici",
            "hedef_mudahale_zamani",
            "gecikmis",
            "olcum_zamani",
            "olusturan",
            "olusturulma_zamani",
            "version",
        )

    def get_makine(self, obj):
        return {
            "id": obj.makine_id,
            "kod": obj.tahmin_kaydi.makine_kodu_snapshot,
            "ad": obj.tahmin_kaydi.makine_adi_snapshot,
        }

    def get_gecikmis(self, obj):
        return gecikmis_mi(
            durum=obj.durum,
            hedef=obj.hedef_mudahale_zamani,
            simdi=self.context.get("now", timezone.now()),
        )


class IsEmriDetaySerializer(IsEmriListeSerializer):
    olaylar = IsEmriOlaySerializer(many=True)
    kaynak_karar = serializers.SerializerMethodField()
    erp_ozeti = serializers.SerializerMethodField()
    tekrarlandi = serializers.SerializerMethodField()

    class Meta(IsEmriListeSerializer.Meta):
        fields = IsEmriListeSerializer.Meta.fields + (
            "tahmin_kaydi_id",
            "baslik",
            "aciklama",
            "politika_surumu",
            "kaynak_karar",
            "manuel_oncelik_override",
            "override_nedeni",
            "planlanan_baslangic_zamani",
            "gercek_baslangic_zamani",
            "tamamlanma_zamani",
            "iptal_zamani",
            "tamamlama_notu",
            "iptal_nedeni",
            "bekleme_nedeni",
            "erp_ozeti",
            "olaylar",
            "guncellenme_zamani",
            "tekrarlandi",
        )

    def get_kaynak_karar(self, obj):
        return {
            "motor_surumu": obj.kaynak_motor_surumu,
            "teknik_aciliyet_skoru": obj.kaynak_teknik_aciliyet_skoru,
            "tedarik_riski_skoru": obj.kaynak_tedarik_riski_skoru,
            "nihai_oncelik_skoru": obj.kaynak_nihai_oncelik_skoru,
            "oncelik_seviyesi": obj.kaynak_oncelik_seviyesi,
            "ana_aksiyon": obj.kaynak_ana_aksiyon,
            "karar_guveni": obj.kaynak_karar_guveni,
            "ana_ariza_tipi": obj.kaynak_ana_ariza_tipi,
        }

    def get_erp_ozeti(self, obj):
        return [
            {
                "parca_kodu": x.parca_kodu_snapshot,
                "parca_adi": x.parca_adi_snapshot,
                "stok_durumu": x.stok_durumu,
                "stok_yeterli": x.stok_yeterli,
                "gerekli_miktar": x.gerekli_miktar,
            }
            for x in obj.tahmin_kaydi.erp_snapshotlari.all()
        ]

    def get_tekrarlandi(self, obj):
        return self.context.get("tekrarlandi", False)
