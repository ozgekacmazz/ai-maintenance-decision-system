# Binary makine arızası deney raporu

## Protokol

AI4I 2020 verisi seed 42 ile stratified train/validation/test olarak %70/%15/%15 ayrıldı. Gerçek sayılar 7.000/1.500/1.500; pozitif sayıları 237/51/51'dir. Kümeler çakışmaz ve 10.000 satırın her biri tam bir kez kullanılır. Model/config seçimi validation PR-AUC ile, threshold seçimi yalnız kazanan modelin validation olasılıklarıyla yapıldı. Test kümesi bundan sonra tek final değerlendirme için açıldı. Önceki 60/20/20 çalışma bu rapor ve metadata tarafından geçersiz kılınmıştır.

## Model karşılaştırması

Accuracy seçimde kullanılmaz. Aşağıdaki precision/recall/F1 değerleri sabit 0,50 threshold'undadır; süreler bu yerel koşuya aittir.

| Kimlik | Class weight | Temel hiperparametreler | PR-AUC | Precision | Recall | F1 | Fit (sn) | Inference (sn) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| logistic_regression_none | None | max_iter=2000 | 0,417589 | 0,6471 | 0,2157 | 0,3235 | 0,0271 | 0,0044 |
| logistic_regression_balanced | balanced | max_iter=2000 | 0,401027 | 0,1523 | 0,7647 | 0,2541 | 0,0226 | 0,0041 |
| random_forest_none | None | n_estimators=400, min_samples_leaf=2 | **0,828301** | 0,9355 | 0,5686 | 0,7073 | 1,6965 | 0,2313 |
| random_forest_balanced | balanced | n_estimators=400, min_samples_leaf=2 | 0,818214 | 0,8947 | 0,6667 | 0,7640 | 2,4182 | 0,1964 |

En yüksek validation PR-AUC nedeniyle `random_forest_none` seçildi. Test sonucu model veya threshold kararını değiştirmek için kullanılmadı.

## Validation threshold karşılaştırması

Kanonik politika validation F1'i maksimize eder; sayısal tolerans içinde eşitlikte daha yüksek recall, ardından daha düşük threshold tercih edilir. 5:1 maliyet yalnız varsayımsal karşılaştırmadır.

| İşletim noktası | Threshold | Precision | Recall | F1 | FP | FN | Pozitif tahmin |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sabit 0,50 | 0,500000 | 0,9355 | 0,5686 | 0,7073 | 2 | 22 | 31 |
| Sabit 0,60 | 0,600000 | 1,0000 | 0,5490 | 0,7089 | 0 | 23 | 28 |
| **Maksimum validation F1** | **0,229583** | **0,8367** | **0,8039** | **0,8200** | **8** | **10** | **49** |
| Recall odaklı (≥0,90) | 0,005625 | 0,1335 | 0,9216 | 0,2333 | 305 | 4 | 352 |
| Varsayımsal 5:1 maliyet | 0,229583 | 0,8367 | 0,8039 | 0,8200 | 8 | 10 | 49 |

Artefaktın kanonik threshold'u `0,22958333333333336` değeridir. Recall odaklı nokta yalnız operasyonel alternatif olarak raporlanır.

## Kilitli test sonucu

Kanonik validation threshold'u değiştirilmeden test kümesine uygulandı:

- Precision: 0,7667
- Recall: 0,9020
- F1: 0,8288
- PR-AUC: 0,9193
- Confusion matrix: TN=1.435, FP=14, FN=5, TP=46

Deney sınırları ve kullanım uyarıları [model kartında](MODEL_CARD_BINARY_FAILURE.md), tam makine-okunabilir değerler `data/metadata/binary_failure_model.json` dosyasındadır.
