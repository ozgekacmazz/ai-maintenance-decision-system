# ADR-003: Model Değerlendirme ve Seçim

## Durum

Kabul edildi.

## Bağlam

Arıza sınıfı dengesizdir ve arıza kaçırmanın operasyonel maliyeti yüksektir. Resmî PDF accuracy kullanılmamasını; precision, recall, PR-AUC ve confusion matrix kullanılmasını zorunlu tutar.

## Karar

Accuracy model seçim veya değerlendirme metriği olarak kullanılmayacaktır.

Kullanılacak ölçütler:

- precision
- recall
- F1
- PR-AUC
- confusion matrix
- false positive
- false negative

Modeller aynı veri bölünmesi, feature seti ve random seed ile karşılaştırılacaktır. Validation verisi model ve threshold seçimi için kullanılacak; test verisi nihai değerlendirmeye kadar görülmeyecektir.

Sınıf dengesizliği `class_weight` ve uygun örnekleme deneyleriyle ele alınacaktır. Örnekleme yalnız eğitim bölümünde yapılacaktır.

## Model adayları

- Logistic Regression: baseline
- Random Forest: PDF önerisi ve ana aday
- Gradient Boosting: alternatif

Isolation Forest, PCA ve TCN ilk teslimat kapsamı dışındaki araştırma backlog'udur.

## Threshold kararı

Nihai threshold validation verisiyle ve operasyonel maliyetlerle seçilir. PDF'deki `0.60` yalnız öneri ve deney adayıdır.

## Açıklanabilirlik

SHAP kullanılacaktır. Kullanıcıya gösterilecek ilk üç faktör mutlak SHAP etkisine göre sıralanacaktır.

## Sonuçlar

Seçim süreci tek bir özet metriğe dayanmaz. Nihai kararın ölçütleri, threshold'u, model sürümü ve hata dağılımı raporlanmalıdır.
