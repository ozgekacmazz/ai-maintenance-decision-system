# Sprint 14 SHAP API entegrasyonu

`POST /api/tahminler/risk/` aynı endpoint ve üst seviye tahmin sözleşmesini korur.
SHAP, modelin hesabına katkıyı açıklar; kesin fiziksel arıza sebebi veya nedensellik
kanıtı değildir.

## Akış ve gating

Kanonik input kopyalanır ve ortak engineered feature frame yalnız bir kez üretilir.
Binary ve failure-type inference ile bütün açıklamalar aynı request içinde yakalanan
model nesnelerini ve aynı prepared frame'i kullanır. Risk eşik altındaysa
failure-type modeli ve hiçbir explainer yüklenmez; `aciklanabilirlik.durum` değeri
`RISK_ESIK_ALTINDA` olur. Riskli istekte binary açıklama zorunludur. Yalnız threshold
aşan HDF/PWF/OSF adayları ve threshold aşan deneysel TWF sinyali açıklanır. RNF için
model, olasılık, threshold veya SHAP yoktur.

Riskli bir isteğin herhangi bir açıklaması shape, additivity, finite değer veya
explainer oluşturma kontrolünden geçmezse kısmi `200` verilmez;
`503 MODEL_HIZMETI_KULLANILAMIYOR` döner. Hata gövdesi ile `X-Trace-ID` eşleşir ve iç
model ayrıntısı içermez.

## Feature sunumu

Her `ilk_etkiler` öğesi teknik transformed `feature`, Türkçe `gorunen_ad`, prepared
frame'den alınan ölçeklenmemiş `original_feature_value`, estimator'ın gördüğü
`model_feature_value`, `birim`, finite `shap_value` ve `yon` alanlarını taşır.
StandardScaler tersine çevrilmez. One-hot H/L/M original değeri boolean, model değeri
ise gerçek transformed 0/1 değeridir. Bilinmeyen feature güvenli `503` üretir.
Tahmin olasılığı aday veya üst seviye tahmin alanında zaten bulunduğu için açıklama
içinde yinelenmez; additivity kontrolü yine aynı inference olasılığına karşı yapılır.

## Cache ve snapshot

Binary ve label-bazlı TWF/HDF/PWF/OSF explainer cache'leri ayrı, lazy ve thread-safe
kilitlerle yönetilir. Anahtar, label yanında gerçek pipeline nesnesidir; model reload
sonrası eski estimator açıklayıcısı yeni modelle kullanılamaz. Başarısız oluşturma
cache'e yazılmaz. Model reseti yalnız ilgili explainer cache'ini temizler. Cache
process-local'dir; çok worker'lı dağıtımda her worker kendi cache'ini ısıtır. Bir
riskli request en fazla beş explainer çalıştırabilir: binary ve dört modellenen tip.

## Artefakt ve runtime sürümü

Joblib/pickle artefaktları scikit-learn `1.8.0` ile üretilmiştir. Eğitim ve inference
runtime'ı aynı exact scikit-learn sürümünde tutulur. Dependency yükseltilecekse
modeller güvenilir veriyle yeniden eğitilmeli, test edilmeli ve yeni model sürümü ile
checksum kullanılarak yayımlanmalıdır. Yalnız requirement sürümünü yükseltip eski
joblib artefaktını kullanmak desteklenen deployment akışı değildir.
Exact dependency pin packaging aşamasındaki korumadır. Serving loader ayrıca tracked
metadata sürümünü çalışan `sklearn.__version__` ile joblib deserialize işleminden önce
karşılaştırır. Uyuşmazlıkta trusted loader çağrılmaz ve istemci iç sürüm ayrıntısı
içermeyen kontrollü `503 MODEL_HIZMETI_KULLANILAMIYOR` alır.

İlk SHAP/Numba çağrısı başlangıç maliyeti taşır; warm-cache çağrıları explainer
oluşturma maliyetini tekrar ödemez. Performans değerlendirmesinde düşük risk toplamı,
ilk/warm yüksek risk, hedef başına açıklama süresi ve UTF-8 response byte boyutu ayrı
ölçülmelidir; gizli veya kişisel veri loglanmamalıdır.

## F12 kontrol listesi

- Request payload, `Authorization`, status ve `X-Trace-ID`
- Binary risk ve ilk üç binary etki
- Threshold aşan güvenilir aday açıklamaları
- TWF `YETERSIZ_DESTEK` uyarısı ve RNF yokluğu
- Original/model değer farkı ve doğru birimler
- İstek süresi ve response byte boyutu
