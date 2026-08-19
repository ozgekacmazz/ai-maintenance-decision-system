# Failure-Type Multi-Label Model Deney Raporu

> Bu belge model eğitim koşusunun tarihsel raporudur; güncel runtime birleşimi için README ve hiyerarşik tahmin belgesine bakın.

## Amaç ve problem tanımı

Sprint 10, AI4I kayıtlarının aynı anda birden fazla fiziksel arıza tipi
taşıyabildiğini kanıtladı. Bu nedenle TWF, HDF, PWF ve OSF için dört bağımsız
binary pipeline'dan oluşan binary-relevance multi-label deney uygulanmıştır.
`NONE` ayrı sınıf değildir; dört tahminin de 0 olmasıdır. RNF rastlantısal
semantiği, 19 toplam desteği ve ana hedef tutarsızlığı nedeniyle modellenmemiştir.

Bu sprint yalnız tip modelini eğitir. Binary risk modeliyle servis seviyesinde
hiyerarşik birleştirme sonraki sprintin kapsamıdır.

## Veri, split ve leakage protokolü

Resmî AI4I verisi, seed 42 ile mevcut `Machine failure` stratified
%70/%15/%15 split fonksiyonundan geçirilmiştir. Train/validation/test sırasıyla
7.000/1.500/1.500 satırdır ve Sprint 8 ile aynı kayıtları içerir.

| Split | TWF | HDF | PWF | OSF |
|---|---:|---:|---:|---:|
| Train | 33 | 82 | 69 | 66 |
| Validation | 8 | 12 | 15 | 17 |
| Test | 5 | 21 | 11 | 15 |

Feature sırası `urun_tipi`, `hava_sicakligi_k`, `proses_sicakligi_k`,
`donus_hizi_rpm`, `tork_nm`, `takim_asinmasi_dk`,
`proses_hava_sicaklik_farki_k`, `acisal_hiz_rad_s`, `mekanik_guc_w` şeklindedir.
Ortak feature engineering kullanılmıştır. `Machine failure`, bütün tip
etiketleri, RNF, UDI, Product ID, sentetik makine ve zaman alanları feature değildir.

Binary stratification her tipin oranını ayrı korumaz. Düşük validation/test
support'ları metriklerde yüksek varyans yaratır ve gerçek saha garantisi vermez.

## Model adayları ve validation seçimi

Dört global adayın her biri aynı aile/class-weight politikasıyla dört ayrı
pipeline eğitmiştir. Logistic Regression `max_iter=2000`; Random Forest 400 ağaç
ve `min_samples_leaf=2` kullanır. Seed 42'dir.

| Aday | TWF PR-AUC | HDF PR-AUC | PWF PR-AUC | OSF PR-AUC | Macro PR-AUC | Macro recall @0,50 |
|---|---:|---:|---:|---:|---:|---:|
| logistic_regression_none | 0,0542 | 0,6738 | 0,8931 | 0,9489 | 0,6425 | 0,4245 |
| logistic_regression_balanced | 0,0610 | 0,7222 | 0,7910 | 0,9651 | 0,6348 | 0,9521 |
| random_forest_none | 0,0401 | 0,9791 | 1,0000 | 0,9797 | **0,7497** | 0,5451 |
| random_forest_balanced | 0,0551 | 0,9881 | 1,0000 | 0,9320 | 0,7438 | 0,6390 |

Yalnız validation macro PR-AUC kullanılarak `random_forest_none` seçilmiştir.
Test sonucu bu kararı, class weight'i veya hiperparametreleri değiştirmemiştir.
Fit ve inference süreleri metadata'da yerel tanımlayıcı bilgi olarak bulunur,
seçim skoru değildir.

## Validation threshold'ları

Kazanan aday belirlendikten sonra her threshold yalnız ilgili validation hedefi
ve olasılıklarında maksimum F1, eşitlikte recall, sonra düşük threshold
politikasıyla seçilmiştir. Sınırdaki örneği kararlı korumak için değerler 15
ondalık basamakta aşağı yönlü normalize edilmiştir.

| Etiket | Seçilen threshold |
|---|---:|
| TWF | 0,050999999999999 |
| HDF | 0,181678661616161 |
| PWF | 0,295124999999999 |
| OSF | 0,248874999999999 |

Sabit 0,50, maksimum-F1 ve recall odaklı alternatiflerin tam karşılaştırması
tracked metadata'dadır. Recall odaklı alternatifler artefakt threshold'u değildir.

## Validation sonuçları

| Etiket | Support | Precision | Recall | F1 | PR-AUC | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| TWF | 8 | 0,0698 | 0,3750 | 0,1176 | 0,0401 | 40 | 5 |
| HDF | 12 | 0,9231 | 1,0000 | 0,9600 | 0,9791 | 1 | 0 |
| PWF | 15 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 0 | 0 |
| OSF | 17 | 0,8947 | 1,0000 | 0,9444 | 0,9797 | 2 | 0 |

Toplu validation: micro precision/recall/F1 `0,5222/0,9038/0,6620`, macro
precision/recall/F1 `0,7219/0,8438/0,7555`, weighted F1 `0,8369`, Hamming loss
`0,0080`, subset accuracy `0,9687`. Ortalama tahmin edilen etiket sayısı `0,060`;
1.420 satırda tip yok, 80 satırda en az bir, 8 satırda birden fazla tip vardır.

## Kilitli test sonuçları

Model ailesi ve threshold'lar kilitlendikten sonra test bir kez değerlendirilmiştir.

| Etiket | Support | Precision | Recall | F1 | PR-AUC | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| TWF | 5 | 0,0345 | 0,4000 | 0,0635 | 0,0419 | 56 | 3 |
| HDF | 21 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 0 | 0 |
| PWF | 11 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 0 | 0 |
| OSF | 15 | 0,8333 | 1,0000 | 0,9091 | 0,9877 | 3 | 0 |

Toplu test: micro precision/recall/F1 `0,4537/0,9423/0,6125`, macro
precision/recall/F1 `0,7170/0,8500/0,7431`, weighted F1 `0,8837`, Hamming loss
`0,0103`, subset accuracy `0,9587`. Ortalama tahmin edilen etiket sayısı `0,072`;
1.397 satırda tip yok, 103 satırda en az bir, 5 satırda birden fazla tip
tahmin edilmiştir. Subset accuracy yoğun negatifler nedeniyle yalnız yardımcıdır.

## FP/FN, support ve RNF yorumu

False positive olmayan bir fiziksel tipi önermek, false negative gerçek fiziksel
tipi kaçırmaktır. HDF/PWF/OSF bu testte toplam yalnız üç FP ve sıfır FN
üretmiştir. TWF ise 56 FP ve 3 FN ile güvenilir değildir. TWF validation/test
support'unun yalnız `8/5` olması nedeniyle tek satır metrikleri büyük oranda
değiştirebilir. Bütün etiketler için saha doğrulaması gerekir.

RNF için pipeline, threshold veya dummy tahmin yoktur. Etiket yalnız raporlanır
ve belirsiz/rastlantısal arıza için genel teknik inceleme politikasına gider.

## Artefakt ve entegrasyon sınırı

Artefakt `ml/artifacts/failure-type-1.0.0.joblib` konumunda Git dışındadır.
`pipelines` tam olarak TWF/HDF/PWF/OSF anahtarlarını, `metadata` ise sürüm,
feature, hedef ve threshold sözleşmesini taşır. SHA-256 ve boyut tracked
metadata'da `1c578e767db57bc35f70e75a6f0e8e42ffb75650e364b668cbbc54eb31070f93`
ve `1.567.126` bayt olarak kayıtlıdır. Sonraki sprintte servis entegrasyonu yapılmadan önce
checksum, iç/dış metadata, pozitif sınıf ve pipeline arayüzü doğrulanmalıdır.

Sunum cümlesi:

> Arıza tiplerini tek sınıfa zorlamak yerine TWF, HDF, PWF ve OSF için dört bağımsız binary modelden oluşan multi-label yaklaşım kullandık. Random Forest model ailesini yalnız 0,7497 validation macro PR-AUC ile, her etiketin threshold'unu ise yalnız kendi validation sonuçlarıyla seçtik. Test kümesini bütün kararlar kilitlendikten sonra bir kez açtık. RNF'yi düşük ve tutarsız desteği nedeniyle öğrenilmiş model çıktısı yapmadık.
