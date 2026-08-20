# Model Kartı: failure-type-1.0.0

## Amaç ve kullanım

Bu model AI4I sensör girdilerinden TWF, HDF, PWF ve OSF fiziksel arıza tipi
olasılıkları üretmek için dört bağımsız Random Forest pipeline'ı kullanır.
Kontrollü demo, araştırma ve insan denetimli bakım karar desteği içindir.

Model tek başına makine durdurma, iş emri, güvenlik-kritik karar, saha garantisi,
farklı ekipman popülasyonuna doğrudan genelleme veya RNF tahmini için
kullanılmamalıdır. Django/API entegrasyonu bu sürümün kapsamında değildir.

## Veri, feature ve hedefler

Kaynak UCI AI4I 2020 sentetik predictive-maintenance veri setidir. Seed 42 ile
`Machine failure` stratified 7.000/1.500/1.500 split kullanılmıştır.

Feature'lar: `urun_tipi`, beş ham sensör alanı, proses-hava sıcaklık farkı,
açısal hız ve mekanik güçtür. `Machine failure`, TWF/HDF/PWF/OSF/RNF,
kimlikler ve sentetik replay alanları leakage nedeniyle feature değildir.

Hedefler sırasıyla TWF, HDF, PWF ve OSF'dir. `NONE`, dört hedefin de threshold
altında kalmasıdır. RNF yalnız 19 kayıt ve ana hedefle 18 tutarsızlık nedeniyle
fiziksel öğrenilmiş hedef değildir; genel teknik inceleme politikasına ayrılır.

## Model ve threshold'lar

Validation macro PR-AUC ile `random_forest_none` seçilmiştir: her hedef için
400 ağaç, `min_samples_leaf=2`, `class_weight=None`, seed 42. Threshold'lar
yalnız validation maksimum-F1, eşitlikte recall ve düşük threshold politikasıyla:

- TWF: `0.050999999999999`
- HDF: `0.181678661616161`
- PWF: `0.295124999999999`
- OSF: `0.248874999999999`

## Validation ve test özeti

| Etiket | Val support | Val F1/PR-AUC | Test support | Test F1/PR-AUC |
|---|---:|---:|---:|---:|
| TWF | 8 | 0,1176 / 0,0401 | 5 | 0,0635 / 0,0419 |
| HDF | 12 | 0,9600 / 0,9791 | 21 | 1,0000 / 1,0000 |
| PWF | 15 | 1,0000 / 1,0000 | 11 | 1,0000 / 1,0000 |
| OSF | 17 | 0,9444 / 0,9797 | 15 | 0,9091 / 0,9877 |

Validation micro/macro F1 `0,6620/0,7555`; test micro/macro F1
`0,6125/0,7431`'dir. Test TWF precision/recall yalnız `0,0345/0,4000` olup model
bu hedef için güvenilir kabul edilmemelidir. HDF/PWF/OSF sonuçları yüksek olsa da
support azdır ve belirsizlik geniştir.

## Bilinen sınırlamalar

- Binary stratification tip prevalanslarını ayrı korumaz.
- Bütün validation/test support'ları küçüktür; TWF özellikle kararsızdır.
- AI4I sentetiktir; gerçek saha, temporal veya ekipmanlar arası genelleme kanıtı yoktur.
- Threshold'lar az sayıda validation pozitifi üzerinde seçilmiştir.
- Runtime binary risk eşiğiyle uçtan uca gating uygular; bu entegrasyon ayrı servis/API testleriyle doğrulanır, model kartındaki çevrimdışı metriklerin kapsamını genişletmez.
- Drift izleme, dış doğrulama ve otomatik yeniden eğitim yoktur.

Saha kullanımından önce temsili gerçek veri, prospektif doğrulama, drift
izleme, hata maliyeti incelemesi ve insan onayı zorunludur. Model çıktısı tek
başına bakım kararı değildir.

## Artefakt güvenliği

Artefakt Git dışı `ml/artifacts/failure-type-1.0.0.joblib` dosyasıdır. Joblib
pickle tabanlıdır ve güvenilmeyen kaynaktan yüklenmemelidir. Deserialization
öncesi SHA-256; sonrasında model/pipeline sürümü, feature/hedef sırası,
threshold ve pipeline anahtarları, `predict_proba`, pozitif sınıf ve tracked
metadata uyumu doğrulanmalıdır.
