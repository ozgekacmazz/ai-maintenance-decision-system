from rest_framework_simplejwt.tokens import RefreshToken


def kullanici_icin_token_cifti(kullanici):
    refresh = RefreshToken.for_user(kullanici)
    refresh["rol"] = kullanici.rol
    access = refresh.access_token
    access["rol"] = kullanici.rol
    return str(access), str(refresh)
