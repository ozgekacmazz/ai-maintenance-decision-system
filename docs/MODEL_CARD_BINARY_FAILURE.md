# Model kartı: Binary makine arızası

## Amaç ve kullanım

`binary-failure-1.0.0`, AI4I sensör alanlarından `Machine failure` olasılığı üreten bir karar destek modelidir. Demo, geliştirme ve kontrollü prototip değerlendirmelerinde kullanılabilir. İnsan onayı olmadan bakım kararı, güvenlik-kritik durdurma, gerçek saha garantisi veya farklı ekipman popülasyonuna doğrudan genelleme için kullanılmamalıdır.

## Veri ve girdiler

Kaynak UCI AI4I 2020 sentetik veri setidir. Kaynak CSV SHA-256 değeri `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`'dir.

Girdiler sırasıyla `urun_tipi`, `hava_sicakligi_k`, `proses_sicakligi_k`, `donus_hizi_rpm`, `tork_nm`, `takim_asinmasi_dk`, `proses_hava_sicaklik_farki_k`, `acisal_hiz_rad_s`, `mekanik_guc_w` alanlarıdır. Sayısal alanlar StandardScaler, ürün tipi OneHotEncoder ile pipeline içinde dönüştürülür. Hedef `makine_arizasi`dır. UDI, Product ID, TWF/HDF/PWF/OSF/RNF, sentetik machine_id/timestamp ve hedef alanı leakage nedeniyle dışlanır.

## Model ve deney

Kazanan model `RandomForestClassifier`dır: 400 ağaç, `min_samples_leaf=2`, `class_weight=None`, seed 42. Veri stratified %70/%15/%15 olarak 7.000/1.500/1.500 satıra ayrılmıştır. Model ailesi validation PR-AUC ile seçilmiştir; accuracy kullanılmamıştır.

Validation maksimum-F1 ve eşitlikte yüksek-recall politikası `0,22958333333333336` threshold'unu seçmiştir. Validation precision/recall/F1/PR-AUC: 0,8367/0,8039/0,8200/0,8283; confusion matrix TN=1.441, FP=8, FN=10, TP=41.

Kilitli test precision/recall/F1/PR-AUC: 0,7667/0,9020/0,8288/0,9193; confusion matrix TN=1.435, FP=14, FN=5, TP=46. False positive gereksiz inceleme/bakım yükü, false negative ise gerçek arızanın kaçırılması anlamına gelir.

## Artefakt güvenliği

Artefakt `ml/artifacts/binary-failure-1.0.0.joblib` altında Git dışındadır. Boyutu 1.390.499 bayt, SHA-256 değeri `72f346974938571eabe3d11253697fd86195c4868fd0c1df89d7e8156080cbdf`'dir. Yalnız güvenilir yerel joblib dosyası; checksum, pipeline sürümü, feature sırası, threshold ve `predict_proba` doğrulandıktan sonra yüklenmelidir. Joblib/pickle güvenilmeyen kaynaktan yüklenmemelidir.

## Sınırlamalar

AI4I sentetiktir; gerçek saha garantisi vermez. Dış doğrulama ve gerçek temporal doğrulama yapılmamıştır. Sentetik timestamp temporal kanıt değildir. Drift izleme ve otomatik yeniden eğitim uygulanmamıştır. Runtime, binary eşik aşıldığında ayrı multi-label arıza tipi modellerini ve pozitif sınıf SHAP açıklamalarını çalıştırır. Model çıktısı insan denetimli karar desteği olarak ele alınmalıdır.
