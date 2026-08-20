# OpenAPI Sözleşmesi

Sprint 21A API sözleşmesi OpenAPI 3.0.3 olarak, veri tabanı veya model artefaktı okunmadan deterministik üretilir.

## Erişim

- Schema: `/api/schema/` (`Accept: application/json` veya YAML)
- Swagger UI: `/api/docs/`

İki endpoint de authenticated kullanıcı gerektirir. Doküman ekranı endpoint envanterini gösterdiği için production ortamında public değildir. Swagger `Authorize` alanına yalnız geçici Bearer JWT girilir; gerçek token veya credential dokümana yazılmaz.

## Üretim ve doğrulama

```bash
python manage.py spectacular --format openapi-json --file /tmp/openapi.json --validate
pytest apps/core/tests/test_openapi.py
```

Canonical dosya repository'de tutulmaz; runtime ve test aynı `ProjectSchemaGenerator` kaynağını kullanır. Sözleşme authentication, yönetim, tahmin, input-domain, iş emri, admin log ve replay gruplarını; query filtrelerini, pagination'ı, optimistic locking isteklerini, JWT'yi ve ortak hata component'ini kapsar.

Backend sensör sıcaklık alanları Kelvin'dir. Celsius yalnız UI sunum/girdi katmanıdır. Response şemalarında parola bulunmaz; parola alanları request-only/write-only olarak tanımlıdır.
