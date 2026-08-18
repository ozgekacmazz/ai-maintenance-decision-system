# Kalıcı tahmin kayıtları

`POST /api/tahminler/risk/` stateless kalır ve veritabanına yazmaz. Makineye bağlı,
denetlenebilir karar izi için `POST /api/tahminler/kayitlar/`; sayfalı okuma için
aynı kaynağın `GET` metodu ve `GET /api/tahminler/kayitlar/{uuid}/` kullanılır.
Aktif `USER` ve `ADMIN` rolleri oluşturabilir ve okuyabilir. Kayıtlar `PUT`,
`PATCH` veya `DELETE` ile değiştirilemez.

## Veri ve snapshot tasarımı

Ana kayıt canlı makine ve kullanıcı FK'lerini `PROTECT` ile tutar. Makine kodu,
adı ve kritiklik ile altı kanonik sensör değeri ve modelde kullanılan türetilmiş
feature'lar olay anındaki değerleriyle ayrıca saklanır. Sonraki canlı makine,
parça veya stok değişiklikleri geçmiş snapshot'ı değiştirmez.

Failure-type sonuçları, ilk üç SHAP etkisi ve ERP bağlamı ayrı ilişkisel child
tablolardır. Bu seçim sorgulanabilirlik, şema bütünlüğü ve audit için tek bir büyük
JSON belgesinden daha güçlüdür. HDF/PWF/OSF yalnız güvenilir aday olduklarında ERP
snapshot üretir. Eşiği aşan TWF eşlemesi deneysel olarak saklanabilir; RNF hiçbir
zaman saklanmaz. Düşük riskte failure-type, SHAP ve ERP child listeleri boştur.
ERP kaydı toplam/kullanılabilir stok, minimum stok, gerekli miktar ve tedarik gününü
saklar; gerçek ERP bağlantısı, stok azaltma, rezervasyon veya sipariş oluşturma yoktur.

## Idempotency ve transaction

Scope ve benzersizlik `(makine, kaynak, idempotency_key)` kapsamındadır; kullanıcı
bu kapsama dahil değildir ve tek şirket varsayımı geçerlidir. Gelecekte multi-tenant
bir yapıda tenant/company alanı constraint'e eklenmelidir. Fingerprint; makine,
ölçüm zamanı, kaynak ve sıralanmış kanonik sensör JSON'unun SHA-256 değeridir.
Fingerprint API yanıtında gösterilmez. İlk istek `201` ve `tekrarlandi=false`, aynı
payload tekrarı aynı ID ile `200` ve `tekrarlandi=true`, farklı payload ise güvenli
`409 IDEMPOTENCY_CAKISMASI` döndürür.

Ön kontrol sonrası ML/SHAP transaction dışında çalışır. Eşzamanlı iki ilk istek bu
kısa transaction tercihi nedeniyle ML inference'ı iki kez çalıştırabilir; bu bir
inference-once garantisi değildir. Kısa transaction içinde
makine kilitlenir, idempotency tekrar kontrol edilir ve bütün snapshot'lar atomik
yazılır. PostgreSQL unique constraint yarış durumundaki son güvencedir. Child hatası
tüm kaydı geri alır; model/validation/auth/404/409 hatalarında kayıt oluşmaz.

Snapshot modellerinin instance `save/delete` ve QuerySet `update/delete` yolları
uygulama katmanında kapalıdır; admin de salt okunurdur. `create` ve `bulk_create`
ilk snapshot üretimi için açıktır. Raw SQL ve doğrudan veritabanı yöneticisi bu
uygulama katmanı korumasının dışındadır ve ayrı DB yetkilendirmesi gerektirir.

## Bakım kararı, liste ve detay

Yeni kayıtlarda versiyonlu bakım kararı aynı transaction içinde immutable snapshot
olarak oluşturulur. Detay tam karar, gerekçe, uyarı ve destekleyici aksiyonları;
liste nihai skor, seviye, ana aksiyon ve karar güvenini taşır. Sprint 15 kayıtlarında
karar bulunmayabilir ve bu alanlar `null` döner. Politika ve formüller
[bakım öncelik motoru belgesindedir](MAINTENANCE_PRIORITY_ENGINE.md).

Liste `sayfa` ve `sayfa_boyutu` ile sayfalanır; `makine_id`, `risk_uyarisi`,
`kaynak`, `olcum_zamani_baslangic`, `olcum_zamani_bitis`, güvenilir `ariza_tipi`,
karar enumları ve nihai skor aralığı filtrelerini kabul eder. Varsayılan iş kuyruğu
nihai skor ve teknik aciliyet azalan, ölçüm zamanı artan, UUID sırasıdır.
Liste yalnız özet taşır; detay sensör, model/threshold, SHAP, failure-type ve ERP
snapshot'larını verir. Trace ID standart hata ve başarı izleme sözleşmesini korur.

## Kapsam sınırı ve F12 kontrolü

İş emri ve stok değişikliği kapsam dışıdır; replay motoru sonraki sprinte bırakılmıştır.
F12'de ilk POST `201`, aynı istek `200`/aynı ID, farklı payload `409`, sayfalı liste,
child detayları, SHAP/ERP snapshot'ları, model sürümü/threshold, trace ID,
`PATCH`/`DELETE` için `405`, response süresi ve boyutu kontrol edilmelidir.
