# ADR-002: İsimlendirme ve Dil

## Durum

Kabul edildi.

## Bağlam

Kullanıcı metinlerinin doğal Türkçe olması gerekir. Kod ve veri modeli ise Türkçe karakterlerin identifier uyumsuzluklarına karşı kararlı bir kurala ihtiyaç duyar.

## Karar

- Markdown açıklamaları ve kullanıcı mesajları doğru Türkçe karakterlerle, doğal Türkçe yazılır.
- Veritabanı tablo ve kolonları Türkçe-ASCII `snake_case` kullanır.
- Python sınıfları `PascalCase`; değişkenler ve alanlar `snake_case` kullanır.
- Teknik rol kodları `USER` ve `ADMIN`dir.
- Kararlı durum ve hata kodları Türkçe-ASCII olur.
- Yerleşik teknoloji ve kütüphane adları özgün biçimleriyle korunur.

Doğru identifier örnekleri:

- `is_emirleri`
- `genel_oncelik`
- `bakim_onceligi`
- `tedarik_onceligi`
- `karar_veren_user_id`
- `olusturulma_zamani`

## Sonuçlar

Bu yaklaşım kullanıcıya doğal Türkçe sunarken kod ve veri modelinde ASCII uyumluluğu sağlar. Terim sözlüğünün uygulama geliştikçe güncel tutulması gerekir.
