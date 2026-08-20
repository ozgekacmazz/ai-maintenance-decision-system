# AI4I 2020 veri profili

> Bu belge veri hazırlama aşamasının tarihsel profilidir; güncel model ve runtime davranışı için README ile model kartlarına bakın.

## Kaynak ve lisans

Veri, UCI Machine Learning Repository'deki **AI4I 2020 Predictive Maintenance Dataset** (dataset ID 601, DOI `10.24432/C5HS5C`) resmi arşivinden 18 Ağustos 2026 tarihinde edinildi. UCI API kaydı son güncellemeyi 14 Şubat 2024 olarak, kaynak sayfa ise **CC BY 4.0** lisansını bildirir. Yerel ham dosya `data/raw/ai4i2020.csv` olup Git dışındadır.

- Boyut: 522.048 bayt
- SHA-256: `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`
- Boyut: 10.000 satır × 14 sütun

## Gerçek şema ve kalite

Ham sütunlar sırasıyla `UDI`, `Product ID`, `Type`, `Air temperature [K]`, `Process temperature [K]`, `Rotational speed [rpm]`, `Torque [Nm]`, `Tool wear [min]`, `Machine failure`, `TWF`, `HDF`, `PWF`, `OSF`, `RNF` şeklindedir.

Kimlik ve tam sayı alanları `int64`, sıcaklık/tork alanları `float64`, Product ID ve Type metindir. Eksik hücre ve tam duplicate satır yoktur. UDI ile Product ID ayrı ayrı 10.000 benzersiz değere sahiptir. Product ID, ürün tipi harfi ve beş basamaklı sayı biçimindedir. Type dağılımı L=6.000, M=2.997, H=1.003'tür. Binary alanların tümü yalnız 0/1 içerir.

| Alan | Min | Maks | Ortalama | Medyan | Std. sapma |
|---|---:|---:|---:|---:|---:|
| Hava sıcaklığı (K) | 295,3 | 304,5 | 300,0049 | 300,1 | 2,0003 |
| Proses sıcaklığı (K) | 305,7 | 313,8 | 310,0056 | 310,1 | 1,4837 |
| Dönüş hızı (rpm) | 1168 | 2886 | 1538,7761 | 1503 | 179,2841 |
| Tork (Nm) | 3,8 | 76,6 | 39,9869 | 40,1 | 9,9689 |
| Takım aşınması (dk) | 0 | 253 | 107,951 | 108 | 63,6541 |

Mutlak sıfırın altında sıcaklık, pozitif olmayan dönüş hızı, negatif tork veya negatif takım aşınması yoktur. Uç değerler otomatik silinmemiştir; bu sprint yalnız tanımlayıcı analiz uygular.

## Hedef dağılımları ve anomaliler

`Machine failure` 339 pozitif (%3,39) ve 9.661 negatif (%96,61) içerir. Arıza tipleri TWF=46 (%0,46), HDF=115 (%1,15), PWF=95 (%0,95), OSF=98 (%0,98), RNF=19 (%0,19) pozitiftir.

- 24 satırda birden fazla arıza tipi pozitiftir; görev bu nedenle doğal olarak multi-label davranış içerir.
- 18 satırda Machine failure=0 iken bir arıza tipi pozitiftir.
- 9 satırda Machine failure=1 iken bütün arıza tipleri sıfırdır.
- 19 RNF kaydının yalnız 1'i Machine failure=1, 18'i Machine failure=0'dır. RNF otomatik düzeltilmez ve ona parça/aksiyon uydurulmaz.

Bu üç durum kalite kapısında **uyarıdır**; veri korunur. Gerçek dosya kalite kapısını engelleyici hata olmadan geçer.

## Hazırlama ve sızıntı sınırları

Ham adlar yüklemeden sonra merkezi sözleşmeyle ASCII Türkçe adlara çevrilir. İki deterministik özellik eklenir:

- `proses_hava_sicaklik_farki_k = proses_sicakligi_k - hava_sicakligi_k`
- `acisal_hiz_rad_s = 2π × donus_hizi_rpm / 60`
- `mekanik_guc_w = tork_nm × acisal_hiz_rad_s`

Binary arıza modelinde Machine failure hedeftir; bütün arıza tipi alanları girdiden çıkarılır. Arıza tipi görevinde Machine failure girdi değildir. UDI ve Product ID hiçbir modelin varsayılan girdisi değildir. Accuracy seçim metriği değildir; sınıf dengesizliği ve precision/recall/F1/PR-AUC değerlendirmesi sonraki sprinttedir. Henüz model eğitilmemiştir.

İşlenmiş demo verisine varsayılan 20 makine (`M-001`…`M-020`) ve UTC 2020-01-01 başlangıçlı beş dakikalık deterministik timestamp eklenir. Bunlar yalnız replay/demo alanlarıdır; gerçek ekipman kimliği, gerçek zaman serisi veya temporal genelleme kanıtı değildir. Ham CSV sırasının gerçek kronoloji olduğu varsayılmaz.
