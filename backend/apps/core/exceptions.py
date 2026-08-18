from rest_framework.exceptions import APIException


class KimlikDogrulamaApiHatasi(APIException):
    status_code = 401
    default_detail = "Kimlik doğrulama gerekli."
    default_code = "authentication_required"


class KaynakCakismasiHatasi(Exception):
    """HTTP katmanında 409'a çevrilebilen domain çakışması."""


class HizmetKullanilamiyorHatasi(Exception):
    pass
