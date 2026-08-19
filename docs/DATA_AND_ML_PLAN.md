# Veri ve Makine Öğrenmesi Planı

> Bu belge tarihsel plan kaydıdır; güncel davranış için README, model kartları, `INPUT_DOMAIN.md` ve aktif API belgelerine bakın.

## Sprint 7 uygulama durumu

AI4I 2020 resmi UCI kaynağından edinilmiş; merkezi veri sözleşmesi, kalite kapısı,
türetilmiş sıcaklık farkı/mekanik güç özellikleri ve Git dışı hazırlama hattı
`ml/` altında uygulanmıştır. Gerçek profil sonuçları için [veri profiline](DATASET_PROFILE.md)
bakın. Model eğitimi, sınıf dengesizliği değerlendirmesi ve nihai split kararı sonraki
sprint kapsamındadır. Sentetik makine ve zaman alanları temporal kanıt değildir.

## Sprint 8 uygulama durumu

Binary `Machine failure` görevi için stratified %70/%15/%15 train/validation/test
ayrımı ve Logistic Regression/Random Forest için `None` ile `balanced` class-weight
deneyleri uygulanmıştır. Model validation PR-AUC ile, threshold validation F1'i
maksimize ederek ve eşitlikte recall'u tercih ederek seçilmiştir. Random Forest
`class_weight=None` seçilmiş, kilitli test bölümü kararlar sonrasında değerlendirilmiş ve sürümlü
joblib artefaktı Git dışında üretilmiştir. Sonuçlar [binary model raporunda](BINARY_MODEL_REPORT.md)
ve makine tarafından okunabilir metadata'da kayıtlıdır. SHAP, tahmin API'si ve
arıza türü modeli sonraki sprintlerin kapsamındadır.

## 1. Durum

Bu belge Sprint 0 planıdır. Dataset indirilmemiş, model eğitilmemiş ve veri hattı geliştirilmemiştir.

## 2. Veri kaynağı ve sınırlar

AI4I 2020 Predictive Maintenance Dataset PDF önerisidir ve demo/replay için proje veri seti olarak seçilmiştir. Gerçek veri dosyaları Git'e eklenmeyecektir.

Veri setinde gerçek makine kimliği ve kronolojik zaman akışı bulunmadığı için sentetik `machine_id` ve `timestamp` üretilecektir. Bunlar yalnız replay/demo içindir; temporal model başarımı, gerçek zaman bağımlılığı veya üretim davranışı için kanıt değildir. PDF'deki 20 makine ve beş dakikalık aralık değerleri yapılandırılabilir önerilerdir.

## 3. Veri kalite kapısı

- Eksik ve tekrarlı kayıtlar denetlenir.
- Fiziksel olarak geçersiz sensör değerleri reddedilir veya açıkça işaretlenir.
- Birimler ve beklenen aralıklar doğrulanır.
- Eğitim ve değerlendirme ayrımları arasında veri sızıntısı engellenir.

## 4. Feature engineering

AI4I alanları Kelvin ve SI birimleriyle kullanıldığında:

- Sıcaklık farkı: `sicaklik_farki_k = proses_sicakligi_k - hava_sicakligi_k`
- Mekanik güç: `mekanik_guc_w = tork_nm × 2 × π × donus_hizi_rpm / 60`

Formüller dönüşüm kodu ve testlerde aynı biçimde korunacaktır. Ham featurelar ile türetilmiş featureların adları ve birimleri model metadata'sında saklanacaktır.

## 5. Hedefler ve arıza türleri

Arıza riski için denetimli ikili sınıflandırma, arıza türü için uygun çok sınıflı veya kural destekli yaklaşım değerlendirilecektir. TWF, HDF, PWF, OSF ve RNF veri analizinde korunur.

RNF için güvenilir parça ilişkisi veriden çıkarılamazsa parça eşlemesi uydurulmaz; çıktı genel teknik inceleme aksiyonuna yönlendirilir.

## 6. Model adayları

- Logistic Regression: baseline
- Random Forest: PDF önerisi ve projenin ana adayı
- Gradient Boosting: ölçülü alternatif

Isolation Forest, PCA ve TCN ilk teslimat kapsamı dışındaki araştırma backlog'udur. PCA tek başına sınıflandırıcı, Isolation Forest denetimli model alternatifi olarak sunulmayacaktır.

## 7. Veri bölünmesi ve sınıf dengesizliği

- Modeller aynı veri bölünmesi, feature seti ve random seed ile karşılaştırılır.
- Validation verisi model ve threshold seçimi için kullanılır.
- Test verisi nihai tarafsız değerlendirmeye kadar kullanılmaz.
- Sınıf dengesizliği zorunlu olarak ele alınır.
- `class_weight` ve uygun örnekleme seçenekleri yalnız eğitim bölümü üzerinde karşılaştırılır.

## 8. Değerlendirme

Accuracy model seçim veya değerlendirme metriği olarak kullanılmayacaktır.

Kullanılacak ölçütler:

- precision
- recall
- F1
- PR-AUC
- confusion matrix
- false positive
- false negative

Nihai seçim, arıza kaçırmanın ve gereksiz bakımın operasyonel maliyetini birlikte dikkate alır.

## 9. Threshold

Nihai threshold validation verisiyle seçilir. PDF'deki `0.60` yalnız öneri ve karşılaştırma adayıdır; sabit gereksinim değildir. Seçilen threshold model sürümüyle ve her karar snapshot'ıyla kaydedilir.

## 10. Açıklanabilirlik

Her tahmin için SHAP etkileri hesaplanır. Kullanıcıya gösterilecek ilk üç faktör mutlak SHAP değerine göre azalan sırada seçilir. Feature adı, gözlenen değer, işaretli SHAP değeri ve etki yönü saklanır.

## 11. Artefakt ve çalışma zamanı

- Model eğitim hattı uygulama çalışma zamanından ayrıdır.
- Model joblib ile kaydedilir ve `.joblib` uzantısı kullanılır.
- Artefakt model sürümü, feature şeması ve threshold metadata'sıyla doğrulanır.
- Uygulama çalışırken model eğitilmez.
- Model artefaktları Git'e eklenmez.

## 12. Replay

Replay, satırları yapılandırılabilir hızla sisteme gönderir ve sentetik kimlik/zaman üretir. Tekrar çalıştırma, sıralama ve duplicate davranışı uygulama geliştirilmeden önce test kabul kriterleriyle netleştirilecektir.
