# SHAP açıklanabilirlik altyapısı

## Amaç ve sınır

Sprint 13, binary makine arızası ve TWF/HDF/PWF/OSF modellerinin tek kayıt
kararlarını ortak, doğrulanmış bir teknik sözleşmeyle açıklayan ML katmanını
oluşturur. Django endpoint entegrasyonu Sprint 14 kapsamındadır. Açıklama modelin
hesabını betimler; gerçek arıza nedenini veya nedenselliği kanıtlamaz.

## SHAP, base value ve katkı

SHAP, bir tahmini referans beklenti olan `base_value` ile feature katkılarının
toplamı olarak ayrıştırır. Pozitif SHAP değeri açıklanan pozitif sınıf riskini
artırır, negatif değer azaltır, `1e-12` mutlak tolerans içindeki değer nötrdür.
Yerel açıklama tek kaydı; global özet validation örneğindeki mutlak katkıların
ortalamasını anlatır. Global önem yüksekliği nedensellik veya müdahale etkisi
değildir.

Bu modellerde sklearn Random Forest `TreeExplainer` çıktısı, SHAP iç model etiketi
`raw` olsa da estimator `predict_proba` uzayına toplanır. Sözleşme bu nedenle
`output_space=probability` yazar ve sonucu pozitif sınıf olasılığına karşı ayrıca
doğrular. `base_value + tam SHAP vektörü toplamı`, model olasılığıyla mutlak ve
bağıl `1e-6` toleransta eşleşmelidir. Tolerans, ağaç toplamındaki floating-point
birikimini kapsarken gerçek shape/sınıf hatalarını gizlemeyecek kadar dardır.
Top-N yalnız gösterim filtresidir; additivity her zaman tam vektörde kontrol edilir.

## Pipeline ve feature uzayı

Pipeline doğrudan TreeExplainer'a verilmez. Ortak feature engineering sonrasında
pipeline `preprocessor` adımı çalıştırılır, `get_feature_names_out()` ile gerçek
sıra alınır ve yalnız `model` estimator'ı açıklanır. Açıklamadaki feature değerleri
dönüştürülmüş model uzayındadır: ölçeklenmiş sayısal değerler ile
`urun_tipi_H/L/M` one-hot değerleri. Kullanıcı dostu ham değer eşlemesi Sprint 14'e
bırakılmıştır. UDI, Product ID, machine_id, timestamp, hedefler ve failure label'ları
model feature'ı değildir ve açıklamaya girmez.

Korelasyonlu feature'larda katkı farklı feature'lar arasında paylaşılabilir.
Özellikle dönüş hızı, açısal hız, tork ve mekanik güç birlikte yorumlanırken tek
feature'ın gerçek sebep olduğu sonucu çıkarılmamalıdır.

## Pozitif sınıf ve SHAP shape normalizasyonu

Yalnız pozitif integer sınıf `1` açıklanır. `classes_` içinde bu değer tam bir kez
bulunmalıdır; eksik, yinelenen veya boolean `True` kontrollü `ExplainabilityError`
üretir. Liste, iki boyutlu array, üç boyutlu array ve `shap.Explanation` çıktıları
tek normalize fonksiyonunda pozitif sınıfın tek boyutlu feature vektörüne çevrilir.
Beklenmeyen shape, feature sayısı uyuşmazlığı, NaN veya Infinity reddedilir.

SHAP 0.52 ile gerçek sklearn sınıflandırıcı çıktısının esas biçimi `values` için
`(1, feature_count, class_count)`, `base_values` için `(1, class_count)` şeklindedir.
İki boyutlu `(1, feature_count)` biçimi yalnız tek-output veya pozitif sınıfı daha
önceden seçilmiş çıktı sözleşmesi olarak kabul edilir; bu biçimde sınıf ekseni yoktur.

## Yerel JSON sözleşmesi

```json
{
  "target": "machine_failure",
  "predicted_probability": 0.7842,
  "base_value": 0.034,
  "output_space": "probability",
  "transformed_feature_space": true,
  "feature_contributions": [
    {
      "feature": "tork_nm",
      "feature_value": 0.42,
      "shap_value": 0.21,
      "direction": "RISKI_ARTIRIR"
    }
  ]
}
```

Katkılar mutlak SHAP değerine göre azalır; eşitlikte feature adı kullanılır.
Bütün sayılar finite `[JSON number]` değerleridir. Açıklama input'u mutate etmez.

## Failure-type politikası

HDF/PWF/OSF ve TWF teknik olarak açıklanabilir. TWF düşük support ve zayıf test
performansı nedeniyle açıklamada `guven_durumu=YETERSIZ_DESTEK` ve
`operasyonel_kullanima_uygun=false` taşır. Bu ML açıklama politikası Sprint 12
backend serving politikasıyla aynı anlamdadır; Sprint 14 entegrasyonunda tek
response eşlemesi korunmalıdır. RNF için öğrenilmiş pipeline yoktur ve açıklama
talebi reddedilir.

TWF güven semantiği bugün ML açıklama katmanında ve backend serving policy içinde
ayrı ayrı gösterilmektedir. Sprint 14 API entegrasyonu bunu tek paylaşılan sözleşmeye
bağlamalı veya metadata üzerinden doğrulamalıdır; değerlerin sessizce farklılaşmasına
izin verilmemelidir.

HDF/PWF/OSF açıklamalarının varlığı saha doğruluğu anlamına gelmez. AI4I sentetik
veridir; gerçek saha, temporal genelleme veya gerçek mekanik nedensellik kanıtı
sunmaz.

## Global rapor ve determinizm

`ml/scripts/generate_shap_report.py`, checksum doğrulanmış hazırlanmış verinin
mevcut seed-42 split'indeki validation bölümünden, ilk satırları almak yerine seed 42
ile tekrarsız rastgele sınırlı örnek seçer. Seçilen kayıtları çalışma sırasını
sabitlemek için daha sonra kaynak indeksine göre sıralar. Binary ve dört fiziksel
hedef için mean absolute SHAP üretir.
Ham satır, kimlik veya büyük SHAP matrisi yazmaz. Metadata; kaynak ve artefakt
checksum'ları, model/pipeline sürümleri, seed, örnek boyutu, feature isimleri ve
analiz sürümünü içerir. `created_at` hariç kanonik JSON içeriğinden SHA-256
fingerprint hesaplanır; aynı parametre iki çalıştırmada aynı fingerprint'i verir.

## Güvenlik, performans ve Sprint 14

Joblib dosyaları yalnız mevcut trusted loader'larla, checksum doğrulaması
deserialization öncesinde yapılarak açılır. Açıklamalar model eğitmez, threshold
ve model seçimini değiştirmez. Hata mesajı yol, traceback veya iç model ayrıntısı
taşımaz.

TreeExplainer oluşturma ve ilk SHAP/Numba kullanımı başlangıç maliyeti yaratabilir.
Mevcut artefaktların `ColumnTransformer` adımı dense çıktı üretir ve gerçek artefakt
smoke testleri bu sözleşmeyi doğrular. Gelecekte bir preprocessor sparse çıktı
üretirse mevcut adapter kontrollü `ExplainabilityError` verir. Yeni bir model
sürümünde sparse-to-dense dönüşüm kararı, bellek sınırı değerlendirilerek ayrıca ele
alınmalıdır.

Sprint 14'te request başına explainer oluşturulmamalı; doğrulanmış artefakt cache
anahtarından ayrı ve thread-safe bir explainer cache tasarlanmalıdır. Cache
geçersizliği model yolu/checksum değişimiyle bağlanmalı, başarısız explainer
cache'e yazılmamalıdır.

F12/API incelemesinde `target`, `predicted_probability`, `base_value`,
`output_space`, `transformed_feature_space`, katkı sırası/direction, TWF uyarısı,
RNF yokluğu, additivity, response boyutu ve açıklama süresi kontrol edilmelidir.
SHAP çıktısı kullanıcıya “kesin arıza nedeni” olarak sunulmamalı ve insan onayının
yerine geçmemelidir.
