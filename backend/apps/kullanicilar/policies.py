from apps.kullanicilar.models import Kullanici


def aktif_admin_mi(kullanici) -> bool:
    return bool(
        kullanici
        and getattr(kullanici, "is_authenticated", False)
        and kullanici.is_active
        and kullanici.rol == Kullanici.Rol.ADMIN
    )


def kullanici_yonetebilir_mi(kullanici) -> bool:
    return aktif_admin_mi(kullanici)
