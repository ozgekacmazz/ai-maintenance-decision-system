from rest_framework import serializers

from apps.bakim.models import ArizaParcaKurali, Parca


def _metin(deger):
    deger = deger.strip()
    if not deger:
        raise serializers.ValidationError("Bu alan boş olamaz.")
    return deger


class MakineOkumaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kod = serializers.CharField(source="makine_kodu")
    ad = serializers.CharField()
    tip = serializers.CharField()
    kritiklik = serializers.IntegerField()
    aktif = serializers.BooleanField()
    olusturulma_zamani = serializers.DateTimeField(source="olusturulma_tarihi")
    guncellenme_zamani = serializers.DateTimeField(source="guncellenme_tarihi")


class MakineSecenegiSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kod = serializers.CharField(source="makine_kodu")
    ad = serializers.CharField()
    aktif = serializers.BooleanField()


class MakineYazmaSerializer(serializers.Serializer):
    kod = serializers.CharField(source="makine_kodu", max_length=50, validators=[])
    ad = serializers.CharField(max_length=150)
    tip = serializers.CharField(max_length=100)
    kritiklik = serializers.IntegerField(min_value=1, max_value=5)
    aktif = serializers.BooleanField(required=False, default=True)

    validate_kod = staticmethod(_metin)
    validate_ad = staticmethod(_metin)
    validate_tip = staticmethod(_metin)


class StokOzetiSerializer(serializers.Serializer):
    stok_adedi = serializers.IntegerField(source="adet")
    kritik_stok_seviyesi = serializers.IntegerField(source="minimum_stok")


class ParcaOkumaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kod = serializers.CharField(source="parca_kodu")
    ad = serializers.CharField()
    aciklama = serializers.CharField()
    aktif = serializers.BooleanField()
    stok = serializers.SerializerMethodField()
    olusturulma_zamani = serializers.DateTimeField(source="olusturulma_tarihi")
    guncellenme_zamani = serializers.DateTimeField(source="guncellenme_tarihi")

    def get_stok(self, nesne):
        try:
            stok = nesne.stok
        except (AttributeError, Parca.stok.RelatedObjectDoesNotExist):
            return None
        return StokOzetiSerializer(stok).data


class ParcaYazmaSerializer(serializers.Serializer):
    kod = serializers.CharField(source="parca_kodu", max_length=50, validators=[])
    ad = serializers.CharField(max_length=150)
    aciklama = serializers.CharField(required=False, allow_blank=True, default="")
    aktif = serializers.BooleanField(required=False, default=True)

    validate_kod = staticmethod(_metin)
    validate_ad = staticmethod(_metin)


class StokOkumaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    parca_id = serializers.IntegerField()
    parca_kodu = serializers.CharField(source="parca.parca_kodu")
    parca_adi = serializers.CharField(source="parca.ad")
    stok_adedi = serializers.IntegerField(source="adet")
    tedarik_suresi_gun = serializers.IntegerField(source="tedarik_gun")
    kritik_stok_seviyesi = serializers.IntegerField(source="minimum_stok")
    olusturulma_zamani = serializers.DateTimeField(source="olusturulma_tarihi")
    guncellenme_zamani = serializers.DateTimeField(source="guncellenme_tarihi")


class StokYazmaSerializer(serializers.Serializer):
    parca_id = serializers.PrimaryKeyRelatedField(
        source="parca", queryset=Parca.objects.all()
    )
    stok_adedi = serializers.IntegerField(source="adet", min_value=0)
    tedarik_suresi_gun = serializers.IntegerField(source="tedarik_gun", min_value=0)
    kritik_stok_seviyesi = serializers.IntegerField(source="minimum_stok", min_value=0)


class KuralOkumaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ariza_tipi = serializers.CharField()
    parca_id = serializers.IntegerField(allow_null=True)
    parca_kodu = serializers.CharField(source="parca.parca_kodu", allow_null=True)
    parca_adi = serializers.CharField(source="parca.ad", allow_null=True)
    onerilen_aksiyon = serializers.CharField()
    gerekli_miktar = serializers.IntegerField()
    tercih_sirasi = serializers.IntegerField()
    aktif = serializers.BooleanField()
    olusturulma_zamani = serializers.DateTimeField(source="olusturulma_tarihi")
    guncellenme_zamani = serializers.DateTimeField(source="guncellenme_tarihi")


class KuralYazmaSerializer(serializers.Serializer):
    ariza_tipi = serializers.ChoiceField(choices=ArizaParcaKurali.ArizaTipi.choices)
    parca_id = serializers.PrimaryKeyRelatedField(
        source="parca", queryset=Parca.objects.all(), allow_null=True, required=False
    )
    onerilen_aksiyon = serializers.CharField()
    gerekli_miktar = serializers.IntegerField(required=False, default=1, min_value=1)
    tercih_sirasi = serializers.IntegerField(required=False, default=1, min_value=1)
    aktif = serializers.BooleanField(required=False, default=True)

    validate_onerilen_aksiyon = staticmethod(_metin)


class AktiflikSerializer(serializers.Serializer):
    aktif = serializers.BooleanField()


class TemelFiltre(serializers.Serializer):
    arama = serializers.CharField(required=False, allow_blank=False)


class MakineFiltre(TemelFiltre):
    aktif = serializers.BooleanField(required=False)
    kritiklik = serializers.IntegerField(required=False, min_value=1, max_value=5)
    sirala = serializers.ChoiceField(
        required=False, choices=("kod", "-kod", "ad", "-ad", "kritiklik", "-kritiklik")
    )

    def validate_sirala(self, value):
        return {"kod": "makine_kodu", "-kod": "-makine_kodu"}.get(value, value)


class ParcaFiltre(TemelFiltre):
    aktif = serializers.BooleanField(required=False)
    sirala = serializers.ChoiceField(
        required=False, choices=("kod", "-kod", "ad", "-ad")
    )

    def validate_sirala(self, value):
        return {"kod": "parca_kodu", "-kod": "-parca_kodu"}.get(value, value)


class StokFiltre(TemelFiltre):
    dusuk_stok = serializers.BooleanField(required=False)
    sirala = serializers.ChoiceField(
        required=False,
        choices=(
            "stok_adedi",
            "-stok_adedi",
            "tedarik_suresi_gun",
            "-tedarik_suresi_gun",
        ),
    )

    def validate_sirala(self, value):
        return {
            "stok_adedi": "adet",
            "-stok_adedi": "-adet",
            "tedarik_suresi_gun": "tedarik_gun",
            "-tedarik_suresi_gun": "-tedarik_gun",
        }[value]


class KuralFiltre(TemelFiltre):
    ariza_tipi = serializers.ChoiceField(
        required=False, choices=ArizaParcaKurali.ArizaTipi.choices
    )
    parca_id = serializers.IntegerField(required=False, min_value=1)
    aktif = serializers.BooleanField(required=False)
    sirala = serializers.ChoiceField(
        required=False, choices=("ariza_tipi", "-ariza_tipi", "parca_id", "-parca_id")
    )
