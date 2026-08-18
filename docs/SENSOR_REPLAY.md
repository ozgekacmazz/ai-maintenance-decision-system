# Deterministik sensör replay altyapısı

## Commit öncesi kalite kanıtı

Otomatik test ve gerçek-artifact smoke ayrı kanıtlardır; yalnız smoke'ta gözlenen bir
davranış otomatik test edilmiş sayılmaz. Bağlı tahmin, karar ve arıza tipi bulunan 1
ve 10 başarılı öğe otomatik endpoint testinde öğe listesi her iki durumda da 6 sorgu
üretir; N+1 yoktur. Gerçek smoke sorgu sayıları liste/detail/öğe için 2/4/6'dır.
Detail metriği aynı dört sorguluk prefetch setinden hesaplanır. Öğe listesindeki sabit
altıncı sorgu oturum varlık/yetki yüklemesi ile pagination ve ilişkili sayfa yükleme
sözleşmesinin parçasıdır.

Dataset dosyası, metadata, checksum, kolon sözleşmesi veya child bulk-create hatası
session-level fatal hazırlama hatasıdır: transaction rollback olur, yarım oturum ve
öğe kalmaz. Tek öğenin validation/model hatası item-level hatadır ve `HATADA_DEVAM`
uygulanır. Runtime boyunca art arda gelen model 503 hataları için circuit-breaker
uygulanmamıştır; maksimum 25 öğelik batch etkisini sınırlar. Session-level model
fail-fast tamamlanmış kabul edilmez.

HDF/PWF/OSF için predicted-positive yalnız `guvenilir_aday=true` snapshot'tır. TWF
için predicted-positive deneysel `esik_asildi=true` sinyalidir. Eşik altı fiziksel
snapshot ve belirsiz fiziksel tip pozitif sayılmaz. RNF yalnız ground-truth sayısıdır;
prediction metriği yoktur. Ground truth yalnız değerlendirme içindir ve inference'a,
model seçimine veya threshold ayarına girmez.

Yerel gerçek PostgreSQL create smoke ölçümleri: cold 3 öğe 75,74 ms, warm 3 öğe
61,96 ms, 250 öğe 129,28 ms, 1000 öğe 288,96 ms. Her boyutta 6 DB sorgusu çalıştı;
öğeler `bulk_create()` ile yazıldı ve her oturum create'i CSV'yi bir kez okudu.
Process-level dataset cache yoktur. Bunlar SLA değildir. Gerçek artifact step
smoke'unda cold batch 497,40 ms, warm batch 160,64 ms ölçüldü. Üç negatif örnekteki
accuracy 1,0 performans kanıtı değildir.

İlk sürüm yalnız `TEK_MAKINE` eşlemesini destekler. Replay tahmininden iş emri
oluşturma kontrollü 409 ile yasaktır. Gelecekte MQTT/Kafka benzeri broker desteği,
mevcut snapshot/claim/idempotency servislerini koruyan ayrı bir ingestion adapter'ı
olarak eklenmelidir.

## Amaç ve mimari

Replay gerçek IoT broker veya background worker değildir. Prepared AI4I kayıtlarını
sınırlı HTTP adımlarıyla kalıcı tahmin servisine veren denetlenebilir sunum ve model
izleme aracıdır. Varsayılan batch 5, mutlak batch 25; varsayılan oturum 250, mutlak
oturum 1000 öğedir. Uzun model çalışırken DB kilidi tutulmaz.

`ReplayOturumu` kontrol aggregate'ı, `ReplayOgesi` dayanıklı kuyruk kaydı,
`ReplayOlayi` immutable audit geçmişidir. Politika sürümü `sensor-replay-1.0.0`.
İş emri otomatik oluşturulmaz, stok değişmez ve makine durdurma komutu üretilmez.

## Gerçek veri sözleşmesi

Prepared veri 10.000 satır, 19 kolon ve 20 sentetik `machine_id` içerir. UTC zaman
aralığı `2020-01-01T00:00:00Z`–`2020-01-02T17:35:00Z`; makine+timestamp duplicate
yoktur. Aynı timestamp'i paylaşan farklı makineler nedeniyle 9.500 timestamp tekrarı
vardır. Global ve makine içi zaman sırası monotondur.

Pozitif etiket sayıları: binary 339, TWF 46, HDF 115, PWF 95, OSF 98, RNF 19.
Mevcut seed 42 split fonksiyonu değişmeden kullanılır: train 7000, validation 1500,
test 1500. Varsayılan replay test split'idir. Seçim timestamp, eşitlikte kaynak satır
indeksiyle sıralanır; ofset/limit sonradan uygulanır. Test replay yalnız değerlendirme
içindir, tuning veya threshold seçimi değildir.

## Dataset ve checksum güvenliği

Mevcut `load_prepared_dataset()` ve tracked `prepared_source_sha256` sözleşmesi
kullanılır. Dosya/metadata/checksum oturum kurulurken doğrulanır; seçilen satırlar
öğe snapshot'larına yazılır ve step sırasında CSV tekrar okunmaz. Dosya yolu veya
beklenen/gerçek checksum hata response'una çıkmaz. Dataset read-only Docker mount'tur.

## Makine ve zaman politikası

İlk sürüm yalnız `TEK_MAKINE` uygular: sentetik `machine_id` DB primary key sayılmaz;
bütün seçili kayıtlar açıkça seçilen aktif DB makinesine yöneltilir. Sentetik kimlik
öğede audit bağlamı olarak korunur. Gelecekte açık bir ESLEME_TABLOSU child modeli
eklenebilir.

Sanal sensör zamanı prepared UTC timestamp'tir ve `TahminKaydi.olcum_zamani` olur.
Claim/başlama/tamamlama alanları gerçek server zamanıdır. Bu iki zaman birbirine
karıştırılmaz.

## Ground truth ve leakage sınırı

Inference girdisi yalnız altı kanonik alandır:

```text
urun_tipi, hava_sicakligi_k, proses_sicakligi_k,
donus_hizi_rpm, tork_nm, takim_asinmasi_dk
```

Binary/TWF/HDF/PWF/OSF/RNF etiketleri ayrı ground-truth snapshot'ında tutulur.
UDI, ürün kodu, sentetik machine ID, timestamp, replay kimliği, ERP/karar/iş emri
alanları modele verilmez. Ground truth yalnız başarılı tahminden sonra metrikte
kullanılır. RNF raporlanır fakat prediction hedefi değildir.

## State machine

```text
HAZIR → CALISIYOR | IPTAL_EDILDI
CALISIYOR → DURAKLATILDI | TAMAMLANDI | HATALI | IPTAL_EDILDI
DURAKLATILDI → CALISIYOR | IPTAL_EDILDI
HATALI → CALISIYOR | IPTAL_EDILDI
TAMAMLANDI/IPTAL_EDILDI → terminal
```

Aynı durum ve izinsiz geçiş 409'dur. Her mutation `beklenen_version`, row lock,
actor ve trace ID kullanır. Başarılı kontrol version'ı artırır.

## Claim, crash ve hata politikası

Step kısa transaction'da oturumu kilitler, tek aktif batch kontrolü yapar, sıradaki
BEKLIYOR öğeleri `skip_locked` ile seçer, rastgele claim token atar ve commit eder.
ML/SHAP/ERP/karar transaction dışında mevcut `tahmin_kaydi_olustur()` ile çalışır.
Her sonuç ayrı kısa transaction'da yalnız token hâlâ eşleşiyorsa yazılır.

Claim timeout 10 dakika, maksimum deneme 3'tür. Stale `ISLENIYOR` öğe yeniden
BEKLIYOR yapılabilir; eski token sonucu yazamaz. Aktif batch varken ikinci step
`409 REPLAY_ADIMI_ZATEN_CALISIYOR` alır. Varsayılan `HATADA_DEVAM`: item hatası
güvenli BASARISIZ olur, diğer öğeler devam eder. Dataset/checksum hatası oturum
oluşmadan 503'tür. Retry yalnız deneme limitinin altındaki başarısızları hazırlar.

Deterministik idempotency key `replay:{oturum_uuid}:{sira}` biçimindedir. Retry aynı
kalıcı tahmini döndürür; duplicate tahmin üretmez. Kaynak `REPLAY`, karar snapshot'ı
normal akışta oluşur. Replay tahmininden manuel iş emri de
`REPLAY_TAHMININDEN_IS_EMRI_OLUSTURULAMAZ` ile reddedilir.

## Metrikler ve veri kalite gözlemi

Yalnız BASARILI ve tahmin bağlantılı öğeler değerlendirilir. Binary confusion sırası
TN/FP/FN/TP'dir. Precision `TP/(TP+FP)`, recall `TP/(TP+FN)`, F1 harmonik ortalamadır;
sıfır paydada 0 kullanılır. Hiç sonuç yoksa binary metrik `null` olur.
HDF/PWF/OSF güvenilir aday, TWF deneysel metrik olarak ayrı raporlanır. RNF yalnız
ground-truth sayısıdır. Bu metrikler model seçimi veya threshold ayarı yapmaz.

İlerleme sayaçları filtered Count ile hesaplanır; yüzde gerçek durum dağılımından
üretilir. Basit oranlar gözlemseldir ve bilimsel drift iddiası değildir. PSI/KL veya
gerçek drift alarmı gelecekte ayrı kalibrasyon gerektirir.

## API ve yetki

```text
POST/GET /api/tahminler/replay-oturumlari/
GET /api/tahminler/replay-oturumlari/{uuid}/
GET /api/tahminler/replay-oturumlari/{uuid}/ogeler/
POST .../{uuid}/baslat|adim|duraklat|devam-et|iptal|basarisizlari-yeniden-dene/
```

Aktif USER/ADMIN okuyabilir; yalnız ADMIN mutation yapabilir. Anonim 401, pasif veya
yetkisiz kullanıcı 403 alır. PUT/PATCH/DELETE 405'tir. Liste durum, oluşturan, split,
makine ve hatalı öğe varlığıyla filtrelenir. Öğe listesi durum, external machine,
binary ground truth ve sıra aralığını destekler. Unknown parametre reddedilir.
Başarılı ilişkili öğe yolu dahil gerçek sabit sorgu sayıları yukarıdaki kalite kanıtı
bölümünde açıklanmıştır.

## F12 akışı ve sınırlamalar

Oturum oluştur, checksum kimliğini ve öğe sayısını gör, başlat, beşli step çalıştır,
sanal/gerçek zamanı ayır, REPLAY tahmininde SHAP/ERP/kararı aç, metrikleri gör,
duraklatılmış step 409'u göster, devam/retry/tamamlama yap, replay iş emri reddini ve
trace ID'yi doğrula. Sistem process-içi bounded HTTP orchestration'dır; Celery,
MQTT/Kafka, otomatik scheduler, canlı cihaz ve bilimsel drift alarmı kapsam dışıdır.
