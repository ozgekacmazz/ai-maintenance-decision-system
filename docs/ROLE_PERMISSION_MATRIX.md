# Rol ve Yetki Matrisi

Bu belge ürün rolleri ile Django'nun teknik kullanıcı bayraklarını ayırır. HTTP API,
JWT, ürün ekranları ve authoritative backend permission kontrolleri uygulanmıştır.

## Kavramlar

- `rol=USER`: operasyonel ürün özelliklerini kullanacak normal ürün rolüdür.
- `rol=ADMIN`: USER yetkilerine ek olarak ürün yönetim işlemlerini yapacak roldür.
- `is_active`: pasifse authentication ve korumalı işlemler reddedilmelidir.
- `is_staff`: Django admin sitesine giriş için gereken teknik bayraktır.
- `is_superuser`: Django izin kontrollerinin tamamını geçen teknik yetkidir.

Aktif bir `ADMIN`, `is_staff=False` olsa da ürün kullanıcı yönetimi policy'sinde
yöneticidir; fakat Django admin sitesine giremez. Tersine, `USER` rolündeki bir
superuser ürün policy'sinde ADMIN sayılmaz. Gizli signal veya model override bu
kavramları birbirine eşitlemez.

| Alan / işlem | Aktif USER | Aktif ADMIN | Django teknik koşulu | Durum |
|---|---:|---:|---|---|
| Risk listesi | Evet | Evet | Ürün authentication | Uygulandı |
| Makine detayı | Evet | Evet | Ürün authentication | Uygulandı |
| İş emirleri | Evet | Evet | Ürün authentication + işlem policy'si | Uygulandı |
| Kullanıcı yönetimi | Hayır | Evet | Aktif ürün ADMIN | Uygulandı |
| Makine/stok yönetimi | Hayır | Evet | Aktif ürün ADMIN | Uygulandı |
| Tahmin logları | Hayır | Evet | Aktif ürün ADMIN | Uygulandı |
| Django admin | Hayır | Ürün rolü tek başına yetmez | `is_active` + `is_staff`; tam yetki için `is_superuser` | Mevcut |

Pasif kullanıcı yeni oturum açamaz veya token yenileyemez. JWT
uygulanan authentication katmanında login, refresh ve korumalı endpoint'lerde
reddedilir. Menü gizlemek güvenlik değildir; her korumalı endpoint
policy/permission kontrolünü sunucuda yapar. Token yokluğu/geçersizliği HTTP 401,
kimliği doğrulanmış kullanıcının ürün rolü eksikliği HTTP 403 döndürür.

`GET /api/auth/admin-kontrol/` bu ayrımı doğrulayan server-side endpoint'tir:
aktif ADMIN 200, USER (superuser olsa bile) 403, tokensız istek 401 alır.

## İlk admin bootstrap akışı

`seed_admin`, geliştirme/demo ortamında `ADMIN_USERNAME`, opsiyonel `ADMIN_EMAIL`
ve zorunlu `ADMIN_PASSWORD` environment değişkenlerinden ilk yöneticiyi oluşturur.
Kullanıcı `ADMIN`, aktif, staff ve superuser olur. Parola Django validator'larından
geçer ve yalnız hash olarak saklanır.

Komut idempotenttir: aynı username ile ikinci kullanıcı oluşturmaz, mevcut
kullanıcının güvenli bootstrap bayraklarını düzeltir ve varsayılan olarak parolayı
değiştirmez. Parola ancak `--update-password` ile yenilenir. `ADMIN_PASSWORD`
Git'e, shell history'ye, komut argümanına veya loglara yazılmamalıdır. Bu akış
production secret yönetiminin yerine geçmez.
