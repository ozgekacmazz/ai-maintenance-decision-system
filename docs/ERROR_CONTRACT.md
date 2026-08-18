# Uygulanan API Hata Sözleşmesi

Sprint 5 itibarıyla `/api/` altındaki hata yanıtları aşağıdaki kararlı biçimdedir:

```json
{
  "hata": {
    "kod": "GECERSIZ_ISTEK",
    "mesaj": "Gönderilen bilgilerde doğrulama hataları var.",
    "alanlar": {"username": ["Bu alan zorunludur."]},
    "trace_id": "0a000000-0000-4000-8000-000000000000"
  }
}
```

- `kod`, frontend kararları için büyük harfli ve ASCII kararlı koddur.
- `mesaj`, kullanıcıya gösterilebilecek güvenli Türkçe metindir.
- `alanlar`, nested serializer yapısını JSON-safe biçimde korur; yoksa `{}` olur.
- `trace_id`, aynı response'un `X-Trace-ID` header'ıyla aynıdır.

| HTTP | Kod | Anlam |
|---:|---|---|
| 400 | `GECERSIZ_ISTEK` | İstek/alan doğrulaması başarısız |
| 401 | `KIMLIK_DOGRULAMA_GEREKLI` | Token veya login doğrulaması başarısız |
| 403 | `YETKI_YETERSIZ` | Kimlik doğrulanmış, ürün rolü yetersiz |
| 404 | `KAYNAK_BULUNAMADI` | API kaynağı bulunamadı |
| 409 | `KAYNAK_CAKISMASI` | Domain veya kayıt çakışması |
| 429 | `ISTEK_SINIRI_ASILDI` | Throttle sınırı aşıldı |
| 500 | `BEKLENMEYEN_SUNUCU_HATASI` | Ayrıntısı gizlenen beklenmeyen hata |
| 503 | `HIZMET_KULLANILAMIYOR` | Bağımlı hizmet geçici olarak kullanılamıyor |

Başarılı response gövdeleri değişmez. Django admin HTML sayfaları sözleşmeye
dönüştürülmez. CSRF reddi ve Django URL 404 yanıtları `/api/` sınırında middleware
tarafından normalize edilir; CSRF kontrolü devre dışı değildir.

Frontend `ApiHatasi` ile status, kod, mesaj, alanlar ve trace ID'yi normalize eder.
JSON olmayan yanıt ve ağ kesintileri güvenli fallback'e çevrilir. 401 mevcut tek
refresh/tek retry akışını başlatır; 403 oturumu kapatmaz. 500 durumunda kullanıcı
destek ekibine trace ID iletebilir. Token, parola veya cookie hata nesnesine girmez.
