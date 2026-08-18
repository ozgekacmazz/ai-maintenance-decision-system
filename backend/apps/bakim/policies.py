from apps.kullanicilar.policies import aktif_admin_mi


def bakim_kaydi_yazabilir_mi(kullanici) -> bool:
    return aktif_admin_mi(kullanici)
