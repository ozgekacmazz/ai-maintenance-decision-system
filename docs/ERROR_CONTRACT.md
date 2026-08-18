# Hata Sözleşmesi

## 1. Amaç

Bu belge API ve kullanıcı arayüzü için planlanan hata sözleşmesini tanımlar. Sözleşme henüz uygulanmamıştır.

## 2. Ortak biçim

```json
{
  "success": false,
  "error": {
    "code": "GECERSIZ_SENSOR_DEGERI",
    "message": "Tork değeri geçerli aralıkta değil.",
    "field_errors": {
      "tork_nm": ["Değer negatif olamaz."]
    },
    "trace_id": "ornek-trace-id",
    "timestamp": "ISO-8601"
  }
}
```

- `code` kararlı ve Türkçe-ASCII bir teknik koddur.
- `message` kullanıcıya yönelik doğal Türkçe metindir.
- `field_errors` yalnız ilgili ve güvenli alan ayrıntılarını içerir.
- `trace_id` destek ve günlük korelasyonu için kullanılır.

## 3. Zorunlu hata durumları

| Durum | Kod | HTTP | Kullanıcı mesajı yaklaşımı |
|---|---|---:|---|
| Eksik sensör verisi | `EKSIK_SENSOR_DEGERI` | 422 | Eksik alanları açıkça belirt |
| Geçersiz sensör değeri | `GECERSIZ_SENSOR_DEGERI` | 422 | Geçerli aralık veya biçimi belirt |
| Model artefaktı bulunamadı | `MODEL_ARTEFAKTI_BULUNAMADI` | 503 | Tahmin hizmetinin geçici olarak kullanılamadığını belirt |
| Model yüklenemedi/uyumsuz | `MODEL_YUKLENEMEDI` | 503 | Teknik ayrıntıyı gizleyip tekrar deneme yönlendirmesi ver |

## 4. Diğer hata kodları

- `DOGRULAMA_HATASI`
- `KIMLIK_DOGRULAMA_BASARISIZ`
- `YETKISIZ_ERISIM`
- `KULLANICI_PASIF`
- `TAHMIN_BULUNAMADI`
- `IS_EMRI_ZATEN_VAR`
- `GECERSIZ_DURUM_GECISI`
- `BAGLANTI_HATASI`

## 5. HTTP durumları

- 400: bozuk istek veya parametre
- 401: kimlik doğrulama başarısız
- 403: rol veya nesne yetkisi yok
- 404: kaynak bulunamadı
- 409: duplicate kayıt veya durum çakışması
- 422: alan ya da iş kuralı doğrulaması başarısız
- 429: istek sınırı aşıldı
- 500: beklenmeyen sunucu hatası
- 503: model veya bağımlı hizmet kullanılamıyor

## 6. Güvenlik ve gözlemlenebilirlik

Hata yanıtları secret, token, parola, yerel dosya yolu veya stack trace içermez. Sunucu günlükleri aynı `trace_id` ile teknik ayrıntıyı kaydeder; kullanıcı mesajı yalın kalır.
