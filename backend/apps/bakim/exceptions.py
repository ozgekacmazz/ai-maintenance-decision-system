from rest_framework.exceptions import ValidationError

from apps.core.exceptions import KaynakCakismasiHatasi


class BakimDogrulamaHatasi(ValidationError):
    """Bakım iş kurallarının güvenli 400 yanıtına çevrilmesini sağlar."""


class IsEmriCakismasiHatasi(KaynakCakismasiHatasi):
    def __init__(self, kod, mesaj):
        super().__init__(mesaj)
        self.kod = kod
        self.mesaj = mesaj


class IsEmriGecisiHatasi(IsEmriCakismasiHatasi):
    def __init__(self, mesaj="İş emri durum geçişi geçersizdir."):
        super().__init__("IS_EMRI_GECISI_GECERSIZ", mesaj)


class EszamanliGuncellemeHatasi(IsEmriCakismasiHatasi):
    def __init__(self):
        super().__init__(
            "ESZAMANLI_GUNCELLEME_CAKISMASI",
            "İş emri başka bir işlem tarafından güncellendi.",
        )
