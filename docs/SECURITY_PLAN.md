# Güvenlik Planı

## 1. Durum

Bu belge Sprint 0 güvenlik kararlarını tanımlar. Kontroller henüz uygulanmamıştır.

## 2. Kimlik doğrulama

- Self-service kayıt olmayacaktır; kullanıcıları ADMIN oluşturur.
- Parolalar Django'nun salt içeren güvenli parola hash mekanizmasıyla saklanır.
- Düz metin parola, token veya secret günlüklere ya da yanıtlara yazılmaz.
- Kısa ömürlü access token kullanılacaktır.
- Refresh token HttpOnly cookie içinde tutulacak; rotation ve blacklist uygulanacaktır.
- Pasif kullanıcıların yeni oturum açması ve token yenilemesi engellenecektir.

## 3. Roller ve sunucu tarafı yetkilendirme

Teknik rol kodları `USER` ve `ADMIN`dir.

| İşlem | USER | ADMIN |
|---|---:|---:|
| Risk listesi ve makine detayı | Evet | Evet |
| İş emirlerini görüntüleme | Evet | Evet |
| Yetkili bakım kararı verme | Evet | Evet |
| Makine/stok yönetimi | Hayır | Evet |
| Tahmin loglarını görüntüleme | Hayır | Evet |
| Kullanıcı yönetimi | Hayır | Evet |

Her korumalı API endpoint'i rolü sunucu tarafında doğrular. Arayüzde menü gizlemek güvenlik kontrolü sayılmaz.

## 4. Onay ve ret denetim izi

Onay ve ret işlemlerinde tahmin, karar türü, karar veren kullanıcı kimliği ve karar zamanı değiştirilemez denetim kaydı olarak saklanır. Onay olmadan iş emri oluşturulmaz.

## 5. Ortam ve secret yönetimi

- Yerel geliştirmede `.env` oluşturulabilir.
- `.env` Git'e eklenmez ve gerçek bağlantı bilgileri koda gömülmez.
- `.env.example` yalnız placeholder değerler içerir.
- Üretim secretları uygun ortam veya secret yönetim hizmetinden sağlanır.

## 6. İzleme ve hata güvenliği

- Her istek uçtan uca `trace_id` ile izlenir.
- Hata mesajları secret, parola, token, stack trace veya yetkisiz veri içermez.
- Kimlik doğrulama hataları kullanıcı varlığını ifşa etmeyen genel mesajlar verir.

## 7. Temel risk kontrolleri

- Yetkisiz admin erişimi: sunucu tarafı rol kontrolü.
- Duplicate iş emri: transaction ve benzersiz kısıt.
- Kötü sensör verisi: veri kalite kapısı.
- Token kötüye kullanımı: kısa ömür, rotation ve blacklist.
- Secret sızıntısı: Git dışı yerel `.env` ve secretsız `.env.example`.

## 8. Sprint 3 kullanıcı yönetimi kontrolleri

- Aktif `ADMIN` ürün rolü kullanıcı yönetebilir; `is_staff` ve `is_superuser`
  ürün policy kararına dahil değildir. Django admin erişimi ayrıca `is_staff`
  gerektirir.
- Kullanıcı oluşturma ve parola yenileme Django parola validator'larını ve hash
  mekanizmasını kullanır. Pasifleştirme kayıt silmez ve yönetici kendi hesabını
  bu servisle pasifleştiremez.
- Development/demo `seed_admin` parolayı yalnız environment'tan alır, çıktıya
  yazmaz ve tekrar çalıştırmada varsayılan olarak değiştirmez.
- Ayrıntılı kararlar [rol ve yetki matrisinde](ROLE_PERMISSION_MATRIX.md) bulunur.

## 9. Sprint 4 authentication kontrolleri

- Beş dakikalık access token yalnız frontend belleğinde; bir günlük refresh token
  yalnız auth path'li HttpOnly cookie içindedir.
- Login, refresh ve logout CSRF cookie + `X-CSRFToken` ile korunur. Credentialed
  CORS yalnız izinli frontend origin'ine açıktır.
- Refresh rotation ve blacklist etkindir. Logout refresh tokenı iptal eder;
  stateless access token kısa ömrü bitene kadar geçerli kalabilir.
- Pasif kullanıcı login, refresh ve access-token kullanıcı doğrulamasında
  reddedilir. 401 authentication, 403 ürün rolü eksikliğidir.
- Production HTTPS için refresh cookie `Secure=True` olmalıdır. Ayrıntılar
  [authentication akışında](AUTH_FLOW.md) belgelenmiştir.
