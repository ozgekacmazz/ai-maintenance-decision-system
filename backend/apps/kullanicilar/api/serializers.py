from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.kullanicilar.models import Kullanici


class GirisSerializer(serializers.Serializer):
    username = serializers.CharField(trim_whitespace=True)
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class KullaniciOzetiSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(required=False)
    rol = serializers.CharField()


class KullaniciYonetimSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kullanici
        fields = ("id", "username", "email", "rol", "is_active", "date_joined")
        read_only_fields = ("id", "date_joined")


def parolayi_dogrula(parola, kullanici, alan):
    try:
        password_validation.validate_password(parola, user=kullanici)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({alan: list(exc.messages)}) from exc


class KullaniciOlusturmaSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = Kullanici
        fields = ("id", "username", "email", "password", "rol", "is_active")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        aday = Kullanici(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
            rol=attrs.get("rol", Kullanici.Rol.USER),
        )
        parolayi_dogrula(attrs.get("password"), aday, "password")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Kullanici(**validated_data)
        user.set_password(password)
        user.save()
        return user


class KullaniciGuncellemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kullanici
        fields = ("rol", "is_active", "email")


class SifreGuncellemeSerializer(serializers.Serializer):
    yeni_sifre = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_yeni_sifre(self, value):
        parolayi_dogrula(value, self.context["kullanici"], "yeni_sifre")
        return value
