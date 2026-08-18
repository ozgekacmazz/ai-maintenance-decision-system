# ADR-004: Kimlik Doğrulama ve Yetkilendirme

## Durum

Kabul edildi.

## Bağlam

Sistem makine, tahmin, karar, stok ve iş emri verileri üzerinde rol bazlı işlem yapar. Resmî PDF USER ve ADMIN ayrımını, admin erişiminin sunucu tarafında korunmasını ve kullanıcıların admin tarafından oluşturulabilmesini ister.

## Karar

- Teknik roller `USER` ve `ADMIN` olacaktır.
- Self-service kullanıcı kaydı olmayacaktır.
- Kullanıcı oluşturma, parola yenileme ve pasife alma işlemlerini ADMIN yapacaktır.
- USER risk listesi, detay ve iş emirleri ekranlarına erişecektir.
- ADMIN bunlara ek olarak makine/stok, tahmin logu ve kullanıcı yönetimine erişecektir.
- Her yetkili işlem sunucu tarafında kontrol edilecektir.
- Parolalar Django'nun salt içeren standart parola hash mekanizmasıyla saklanacaktır.
- Kısa ömürlü access token ve HttpOnly cookie içinde refresh token kullanılacaktır.
- Refresh token rotation ve blacklist uygulanacaktır.

## Karar denetimi

Onay veya ret işlemi kullanıcı kimliği ve zamanıyla saklanacaktır. Kullanıcı onayı olmadan iş emri oluşturulmayacaktır.

## Ortam güvenliği

Yerel `.env` oluşturulabilir ancak Git'e eklenmez. `.env.example` yalnız placeholder içerir. Secretlar koda veya izlenen dosyalara yazılmaz.

## Sonuçlar

Sunucu tarafı izin kontrolleri tüm korumalı endpoint'lerde uygulanmalıdır. Pasif kullanıcıların giriş ve token yenileme davranışı engellenmelidir. Rotation ve blacklist ek uygulama ve test maliyeti getirir; bu güvenlik maliyeti kabul edilmiştir.
