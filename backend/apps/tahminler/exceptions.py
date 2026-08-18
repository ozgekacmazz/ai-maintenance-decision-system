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
