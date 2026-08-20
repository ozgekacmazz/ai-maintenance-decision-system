# Mimari

## 1. Durum

Bu belge çalışan sistemin güncel mimarisini tanımlar. Tarihsel karar gerekçeleri `docs/decisions/` altındaki ADR'lerde korunur.

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

1. Sensör verisi API'ye Kelvin birimiyle gelir veya replay snapshot'ından alınır; web Hızlı Analiz Celsius'u Kelvin'e dönüştürür.
2. Sürümlü input-domain contract fiziksel ve supported sınırları doğrular.
3. Binary model risk skorunu üretir; eşik aşılırsa multi-label fiziksel modeller çalışır.
4. SHAP binary ve çalıştırılan fiziksel modellerin pozitif sınıf çıktısını açıklar.
5. `TahminKaydi`, model sonucu ve immutable failure/SHAP/ERP snapshot'ları yazılır.
6. Legacy açıklama skorları ile canonical 1–5 genel öncelik ayrı alanlarda hesaplanır.
7. Kullanıcı tahmini onaylar veya reddeder; karar aktör ve zamanla kaydedilir.
8. Yalnız onaydan sonra iş emri, kaynak/etkin öncelik ve canonical SLA oluşur.
9. ADMIN override yalnız etkin öncelik/deadline'ı değiştirir ve immutable audit olayı üretir.

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

## 11. Sprint 9 ML inference sınırı

`apps.tahminler` HTTP doğrulamasını ve inference servis sınırını bakım CRUD
modüllerinden ayrı tutar. Servis, dış metadata'yı ve artefakt SHA-256 değerini
joblib deserialization işleminden önce doğrular; ardından `bakim_ml` paketinin
güvenilir artefakt ve feature engineering fonksiyonlarını yeniden kullanır.
Doğrulanmış model process içinde kilitli lazy cache ile bir kez yüklenir.
Tahmin sonucu bu sprintte veritabanına yazılmaz. Modelin bulunmaması genel sağlık
kontrolünü düşürmez; tahmin isteği güvenli ve izlenebilir bir `503` alır.

## 12. Sprint 12 hiyerarşik inference

Tek risk endpoint'i ortak feature frame'i üzerinde önce binary modeli çalıştırır.
Failure-type modeli yalnız risk uyarısında ayrı doğrulanmış lazy cache'ten alınır.
HDF/PWF/OSF operasyonel aday, TWF deneysel sinyal, RNF model dışıdır. Güvenilir
aday bulunmazsa sonuç belirsiz fiziksel tip olarak işaretlenir. Riskli istekte
ikinci model kullanılamıyorsa kısmi başarı yerine standart `503` döner. Ayrıntılı
akış, sınırlamalar ve F12 listesi [hiyerarşik tahmin belgesindedir](HIERARCHICAL_PREDICTION_FLOW.md).

## 13. Sprint 14 açıklama entegrasyonu

Risk gating sonrasında aynı prepared feature frame ve aynı model snapshot'ı
kullanılarak SHAP açıklamaları atomik response'a eklenir. Model nesnesine bağlı
binary ve label-bazlı explainer cache'leri process-local, ayrı ve thread-safe'dir.
TWF operasyonel güven semantiğinin tek kaynağı backend serving policy'dir; ML
katmanı yalnız matematiksel katkı üretir. Ayrıntılar
[entegrasyon belgesindedir](SHAP_API_INTEGRATION.md).

## Kalıcı karar izi

Stateless inference ile makineye bağlı immutable karar kayıtları ayrıdır. Ana kayıt,
ilişkisel failure-type/SHAP/ERP snapshot'ları, transaction sınırı ve canlı FK ile
olay snapshot'ı ayrımı [kalıcı tahmin mimarisi belgesinde](PREDICTION_RECORDS.md)
açıklanır.

Kalıcı tahmin oluşturulurken DB ve request bağımsız `maintenance-priority-1.0.0`
kural motoru yalnız bu snapshot'ları kullanır. Teknik aciliyet, tedarik riski ve nihai
öncelik ayrı hesaplanır; karar/gerekçe/aksiyon/uyarı ilişkisel immutable snapshot'ları
aynı kısa transaction içinde yazılır. Tasarım ve formüller
[bakım öncelik motoru belgesindedir](MAINTENANCE_PRIORITY_ENGINE.md).

İş emri bu immutable geçmişten ayrı, kontrollü güncellenebilir aggregate'tır. Durum,
atama ve etkin öncelik yalnız kilitli domain servisleriyle değişir; her değişiklik
immutable olay üretir. Ayrıntılar [iş emri yaşam döngüsündedir](WORK_ORDER_WORKFLOW.md).

Replay, tahmin domaininde oturum/öğe/immutable olay olarak modellenir. Dataset yalnız
oturum kurulurken okunur; claim transaction'ı ile uzun inference birbirinden ayrılır.
Ayrıntılar [sensör replay belgesindedir](SENSOR_REPLAY.md).

## Öncelik karar zinciri

Sensör tahmini canonical formülü çalıştırır ve immutable bakım kararı snapshot'ına 1–5 genel öncelik ile formül girdilerini yazar. İş emri bu snapshot'ın kaynak değerlerini kopyalar, etkin önceliği başlatır ve sürümlü SLA politikasından deadline üretir. Admin override kilitli iş emri satırında yalnız etkin önceliği ve deadline'ı değiştirir; immutable olay snapshot'ı önceki/yeni değeri kaydeder. Legacy snapshot ve emirler nullable canonical sınırında tutulur ve otomatik backfill edilmez.
