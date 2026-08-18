from apps.core.exceptions import HizmetKullanilamiyorHatasi, KaynakCakismasiHatasi


class ModelHizmetiHatasi(HizmetKullanilamiyorHatasi):
    kod = "MODEL_HIZMETI_KULLANILAMIYOR"
    mesaj = "Risk tahmin hizmeti geçici olarak kullanılamıyor."


class IdempotencyCakismasiHatasi(KaynakCakismasiHatasi):
    kod = "IDEMPOTENCY_CAKISMASI"
    mesaj = "Idempotency anahtarı farklı bir istek için kullanılmış."


class KararMotoruHatasi(HizmetKullanilamiyorHatasi):
    kod = "KARAR_MOTORU_KULLANILAMIYOR"
    mesaj = "Bakım karar hizmeti geçici olarak kullanılamıyor."


class ReplayCakismasiHatasi(KaynakCakismasiHatasi):
    def __init__(self, kod, mesaj):
        super().__init__(mesaj)
        self.kod = kod
        self.mesaj = mesaj


class ReplayVeriSetiHatasi(HizmetKullanilamiyorHatasi):
    kod = "REPLAY_VERI_SETI_KULLANILAMIYOR"
    mesaj = "Replay veri seti geçici olarak kullanılamıyor."
