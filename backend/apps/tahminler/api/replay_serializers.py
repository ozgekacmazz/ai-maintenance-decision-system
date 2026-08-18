from rest_framework import serializers
from rest_framework.fields import empty

from apps.bakim.models import Makine
from apps.tahminler.models import ReplayOgesi, ReplayOturumu
from apps.tahminler.replay_policy import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_SESSION_LIMIT,
    MAX_BATCH_SIZE,
    MAX_SESSION_LIMIT,
    replay_metrics,
)


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        unknown = sorted(set(data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {x: ["Beklenmeyen alan."] for x in unknown}
            )
        return super().to_internal_value(data)


class QueryBoolean(serializers.BooleanField):
    default_empty_html = empty


class ReplayOlusturmaSerializer(StrictSerializer):
    split = serializers.ChoiceField(
        choices=("test", "validation", "all"), default="test"
    )
    baslangic_ofseti = serializers.IntegerField(min_value=0, default=0)
    kayit_sayisi = serializers.IntegerField(
        min_value=1, max_value=MAX_SESSION_LIMIT, default=DEFAULT_SESSION_LIMIT
    )
    varsayilan_batch_boyutu = serializers.IntegerField(
        min_value=1, max_value=MAX_BATCH_SIZE, default=DEFAULT_BATCH_SIZE
    )
    sanal_aralik_saniye = serializers.IntegerField(
        min_value=1, max_value=86400, default=60
    )
    makine_id = serializers.PrimaryKeyRelatedField(
        source="makine", queryset=Makine.objects.filter(aktif=True)
    )

    def validate(self, attrs):
        attrs["makine_id"] = attrs.pop("makine").pk
        return attrs


class VersionSerializer(StrictSerializer):
    beklenen_version = serializers.IntegerField(min_value=1)


class IptalSerializer(VersionSerializer):
    iptal_nedeni = serializers.CharField(max_length=500, allow_blank=False)


class AdimSerializer(VersionSerializer):
    batch_boyutu = serializers.IntegerField(
        required=False, min_value=1, max_value=MAX_BATCH_SIZE
    )


class ReplayFiltreSerializer(StrictSerializer):
    durum = serializers.ChoiceField(required=False, choices=ReplayOturumu.Durum.choices)
    olusturan_id = serializers.IntegerField(required=False, min_value=1)
    split = serializers.ChoiceField(
        required=False, choices=("test", "validation", "all")
    )
    makine_id = serializers.IntegerField(required=False, min_value=1)
    hatali_oge_var = QueryBoolean(required=False)
    sirala = serializers.ChoiceField(
        required=False,
        choices=(
            "olusturulma_zamani",
            "-olusturulma_zamani",
            "baslatilma_zamani",
            "-baslatilma_zamani",
            "basarili_sayisi",
            "-basarili_sayisi",
            "basarisiz_sayisi",
            "-basarisiz_sayisi",
            "toplam_oge",
            "-toplam_oge",
            "durum",
            "-durum",
        ),
    )


class ReplayOgeFiltreSerializer(StrictSerializer):
    durum = serializers.ChoiceField(required=False, choices=ReplayOgesi.Durum.choices)
    external_machine_id = serializers.CharField(required=False, max_length=50)
    ground_truth_binary = QueryBoolean(required=False)
    sira_baslangic = serializers.IntegerField(required=False, min_value=1)
    sira_bitis = serializers.IntegerField(required=False, min_value=1)


class ReplayOgeSerializer(serializers.ModelSerializer):
    risk_uyarisi = serializers.SerializerMethodField()
    oncelik_seviyesi = serializers.SerializerMethodField()

    class Meta:
        model = ReplayOgesi
        exclude = ("processing_token", "sensor_snapshot")

    def get_risk_uyarisi(self, obj):
        return obj.tahmin_kaydi.risk_uyarisi if obj.tahmin_kaydi_id else None

    def get_oncelik_seviyesi(self, obj):
        if not obj.tahmin_kaydi_id:
            return None
        return obj.tahmin_kaydi.bakim_karari.oncelik_seviyesi


class ReplayOturumuSerializer(serializers.ModelSerializer):
    ilerleme = serializers.SerializerMethodField()
    makine = serializers.SerializerMethodField()

    class Meta:
        model = ReplayOturumu
        exclude = ("aktif_claim_token",)

    def get_makine(self, obj):
        return {"id": obj.makine_id, "kod": obj.makine.makine_kodu, "ad": obj.makine.ad}

    def get_ilerleme(self, obj):
        counts = {}
        for key, value in (
            ("bekleyen", "BEKLIYOR"),
            ("isleniyor", "ISLENIYOR"),
            ("basarili", "BASARILI"),
            ("basarisiz", "BASARISIZ"),
            ("atlandi", "ATLANDI"),
        ):
            annotation = f"{key}_sayisi"
            counts[key] = (
                getattr(obj, annotation)
                if hasattr(obj, annotation)
                else obj.ogeler.filter(durum=value).count()
            )
        done = counts["basarili"] + counts["basarisiz"] + counts["atlandi"]
        return {**counts, "tamamlanma_yuzdesi": round(done / obj.toplam_oge * 100, 2)}


class ReplayDetaySerializer(ReplayOturumuSerializer):
    metrikler = serializers.SerializerMethodField()
    olaylar = serializers.SerializerMethodField()
    son_ogeler = serializers.SerializerMethodField()

    class Meta(ReplayOturumuSerializer.Meta):
        exclude = ("aktif_claim_token",)

    def get_metrikler(self, obj):
        records = []
        for item in obj.ogeler.all():
            if item.durum != "BASARILI" or not item.tahmin_kaydi_id:
                continue
            predicted = {
                snapshot.kod
                for snapshot in item.tahmin_kaydi.ariza_tipleri.all()
                if (
                    snapshot.kod == "TWF"
                    and snapshot.esik_asildi
                    or snapshot.kod != "TWF"
                    and snapshot.guvenilir_aday
                )
            }
            records.append(
                {
                    "truth": item.ground_truth_snapshot,
                    "risk_uyarisi": item.tahmin_kaydi.risk_uyarisi,
                    "predicted_labels": predicted,
                }
            )
        return replay_metrics(records)

    def get_olaylar(self, obj):
        return [
            {
                "olay_tipi": x.olay_tipi,
                "onceki_durum": x.onceki_durum,
                "yeni_durum": x.yeni_durum,
                "version": x.version,
                "olusturulma_zamani": x.olusturulma_zamani,
            }
            for x in obj.olaylar.all()
        ]

    def get_son_ogeler(self, obj):
        return ReplayOgeSerializer(list(obj.ogeler.all())[-10:], many=True).data
