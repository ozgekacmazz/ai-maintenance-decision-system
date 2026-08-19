from apps.kullanicilar.models import Kullanici
from apps.kullanicilar.policies import aktif_admin_mi


def aktif_bakim_kullanicisi_mi(kullanici) -> bool:
    return bool(
        kullanici
        and getattr(kullanici, "is_authenticated", False)
        and kullanici.is_active
        and kullanici.rol in {Kullanici.Rol.USER, Kullanici.Rol.ADMIN}
    )


def bakim_kaydi_yazabilir_mi(kullanici) -> bool:
    return aktif_admin_mi(kullanici)
