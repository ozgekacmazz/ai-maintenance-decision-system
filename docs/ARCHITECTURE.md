# Mimari

## 1. Durum

Bu belge Sprint 0 mimari kararlarını tanımlar. Bileşenler henüz kurulmamış veya geliştirilmemiştir.

## 2. Teknoloji kararı

PDF teknoloji seçimini geliştiriciye bırakır; FastAPI ve Streamlit yalnız öneridir. Proje kararı:

- Backend: Python, Django ve Django REST Framework
- Frontend: React, TypeScript ve Vite
- Veritabanı: PostgreSQL
- Veri ve ML: pandas, scikit-learn, joblib ve SHAP
- Yerel orkestrasyon: Docker Compose
- API belgeleme: OpenAPI

## 3. Sistem bileşenleri

### 3.1 Web arayüzü

Giriş, risk listesi, makine detayı, iş emirleri ve admin ekranlarını sunar. UI rol kontrolü kullanıcı deneyimini düzenler; güvenlik kararı sunucu tarafında verilir.

### 3.2 API

Kimlik doğrulama, rol kontrolü, sensör validasyonu, tahmin, açıklama, öncelik, onay/ret ve iş emri işlemlerini yürütür.

### 3.3 Veri katmanı

Kullanıcı, makine, stok, arıza–parça eşlemesi, tahmin, karar ve iş emri verilerini saklar. Onay/ret denetim izi ile karar snapshot'ı korunur.

### 3.4 ML çıkarım katmanı

Sürümü doğrulanmış `.joblib` artefaktını joblib ile yükler. Uygulama çalışırken eğitim yapmaz. SHAP etkilerini hesaplar ve mutlak değere göre ilk üç faktörü döndürür.

### 3.5 Replay bileşeni

Demo verisini satır satır API'ye gönderir. Sentetik `machine_id` ve `timestamp` üretir; bunlar gerçek zaman serisi modellemesinde kullanılmaz.

## 4. Ana işlem akışı

1. Sensör verisi API'ye gelir veya replay tarafından gönderilir.
2. Veri kalite kapısı eksik, tekrarlı ve fiziksel olarak geçersiz değerleri denetler.
3. Model artefaktı yüklenir ve tahmin üretilir.
4. Eşik üzerindeki tahmin risk uyarısı olarak kaydedilir.
5. Mutlak SHAP etkisine göre ilk üç faktör belirlenir.
6. Genel öncelik risk, makine kritikliği ve stok katsayısıyla hesaplanıp 1–5 tam sayıya dönüştürülür.
7. Bakım ve tedarik alt skorları genel önceliği açıklar.
8. Kullanıcı taslağı onaylar veya reddeder.
9. Onay ve ret kullanıcı kimliği ve zamanıyla kaydedilir.
10. Yalnız onaydan sonra iş emri oluşturulur.

## 5. Veri modelinin asgari kavramları

- `users`: `username`, `password_hash`, `role`, `status`
- `makineler`: `makine_kodu`, `ad`, `tip`, `kritiklik`
- `stok`: `parca_kodu`, `ad`, `adet`, `tedarik_gun`
- `ariza_parca`: `ariza_tipi`, `parca_kodu`, `onerilen_aksiyon`
- `tahminler`: risk, arıza türü, threshold, genel öncelik, alt skorlar, model sürümü ve açıklama snapshot'ı
- `kararlar`: tahmin, karar türü, karar veren kullanıcı ve karar zamanı
- `is_emirleri`: onaylanan tahmin, makine, aksiyon, parça, öncelik, durum ve oluşturulma zamanı

Kesin tablo ve kolonlar uygulama sprintinde migration tasarımıyla netleştirilecektir.

## 6. Öncelik mimarisi

`ham_genel_oncelik = ariza_riski × makine_kritikligi × stok_katsayisi`

Ham değer yapılandırılmış eşiklerle 1–5 tam sayıya çevrilir. `bakim_onceligi` ve `tedarik_onceligi` açıklayıcı alt skorlardır; kanonik sıralama alanı `genel_oncelik`tir.

## 7. Arıza–parça yaklaşımı

TWF, HDF, PWF ve OSF için doğrulanmış parça/aksiyon eşlemeleri kullanılacaktır. RNF veri analizinde korunur. RNF için bilimsel olarak savunulabilir bir parça eşlemesi belirlenemezse parça uydurulmaz; genel teknik inceleme aksiyonu üretilir.

## 8. Entegrasyon sınırı

İlk sürüm gerçek ERP sistemine bağlanmaz. İç makine, stok, parça ve iş emri modeli ile API sözleşmeleri gelecekteki ERP adaptörüne uygun tasarlanır.

## 9. Yatay kurallar

- USER ve ADMIN izinleri her endpoint'te sunucu tarafında denetlenir.
- Her istek `trace_id` ile izlenir.
- Aynı tahminden birden fazla iş emri oluşturulması transaction ve benzersiz kısıtla engellenir.
- Yerel `.env` Git dışında tutulur; yalnızca yer tutucu değerler içeren ve gizli bilgi içermeyen `.env.example` izlenir.

## 10. Sprint 2 uygulama modülleri

- `apps.kullanicilar`, Django `AbstractUser` tabanlı özel kullanıcı modelini ve
  ürün rolünü içerir. Ürün rolü ile Django admin/staff yetkileri ayrıdır.
- `apps.bakim`, makine, parça, güncel stok snapshot'ı ve arıza–parça kurallarını
  içerir. İlişkiler ve PostgreSQL bütünlük kuralları
  [ER diyagramında](ER_DIAGRAM.md) belgelenmiştir.
- API kullanım senaryoları, authentication ve CRUD uçları Sprint 2 kapsamında
  değildir; mevcut health API değişmeden korunur.
