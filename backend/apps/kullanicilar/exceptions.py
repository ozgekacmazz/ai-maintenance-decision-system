class KullaniciYonetimiHatasi(Exception):
    """Kullanıcı yönetimi kullanım senaryolarının temel hatası."""


class YetkisizKullaniciYonetimiHatasi(KullaniciYonetimiHatasi):
    pass


class GecersizRolHatasi(KullaniciYonetimiHatasi):
    pass


class TekrarlananKullaniciAdiHatasi(KullaniciYonetimiHatasi):
    pass


class GecersizParolaHatasi(KullaniciYonetimiHatasi):
    pass


class KendiHesabiniPasifeAlmaHatasi(KullaniciYonetimiHatasi):
    pass
