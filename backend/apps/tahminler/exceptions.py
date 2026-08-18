from apps.core.exceptions import HizmetKullanilamiyorHatasi


class ModelHizmetiHatasi(HizmetKullanilamiyorHatasi):
    kod = "MODEL_HIZMETI_KULLANILAMIYOR"
    mesaj = "Risk tahmin hizmeti geçici olarak kullanılamıyor."
