from django.http import JsonResponse

STATUS_HATALARI = {
    400: ("GECERSIZ_ISTEK", "Gönderilen istek geçerli değil."),
    401: ("KIMLIK_DOGRULAMA_GEREKLI", "Kimlik doğrulama gerekli."),
    403: ("YETKI_YETERSIZ", "Bu işlem için gerekli yetkiye sahip değilsiniz."),
    404: ("KAYNAK_BULUNAMADI", "İstenen kaynak bulunamadı."),
    409: ("KAYNAK_CAKISMASI", "İşlem mevcut kaynakla çakışıyor."),
    429: ("ISTEK_SINIRI_ASILDI", "Çok fazla istek gönderildi. Lütfen bekleyin."),
    500: ("BEKLENMEYEN_SUNUCU_HATASI", "Beklenmeyen bir sunucu hatası oluştu."),
    503: ("HIZMET_KULLANILAMIYOR", "Hizmet geçici olarak kullanılamıyor."),
}


def hata_govdesi(*, status_code, trace_id, alanlar=None, mesaj=None, kod=None):
    varsayilan_kod, varsayilan_mesaj = STATUS_HATALARI.get(
        status_code, ("GECERSIZ_ISTEK", "İstek tamamlanamadı.")
    )
    return {
        "hata": {
            "kod": kod or varsayilan_kod,
            "mesaj": mesaj or varsayilan_mesaj,
            "alanlar": alanlar or {},
            "trace_id": trace_id,
        }
    }


def json_hata_response(*, status_code, trace_id):
    return JsonResponse(
        hata_govdesi(status_code=status_code, trace_id=trace_id), status=status_code
    )
