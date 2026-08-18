# Sprint 10 Arıza Tipi Etiket Analizi

## 1. Amaç

Bu sprint, AI4I 2020 veri setindeki `TWF`, `HDF`, `PWF`, `OSF` ve `RNF`
etiketlerinin yapısını tekrarlanabilir kodla inceleyip gelecek modelleme sprinti
için problem tanımı üretir. Model eğitimi, threshold seçimi ve test performansı
kararı bu analizin kapsamında değildir.

## 2. Etiketlerin anlamları

- `TWF`: takım aşınması arızası.
- `HDF`: ısı dağılımı arızası.
- `PWF`: güç arızası.
- `OSF`: aşırı zorlanma arızası.
- `RNF`: veri setinin rastlantısal arıza etiketi; belirli bir sensör fiziğine
  bağlı mekanizma olarak tanımlanmamıştır.

## 3. Gerçek sayımlar

Hazırlanmış 10.000 satır üzerinden hesaplanan sonuçlar:

| Etiket | Pozitif | Negatif | Pozitif oranı |
|---|---:|---:|---:|
| TWF | 46 | 9.954 | %0,46 |
| HDF | 115 | 9.885 | %1,15 |
| PWF | 95 | 9.905 | %0,95 |
| OSF | 98 | 9.902 | %0,98 |
| RNF | 19 | 9.981 | %0,19 |

`Machine failure` dağılımı 339 pozitif ve 9.661 negatiftir. Etiket
cardinality değeri `0,0373`, beş hedefe göre density değeri `0,00746`'dır.

## 4. Etiket kombinasyonları ve multi-label kanıtı

9.652 satırda tip etiketi yoktur, 324 satırda tam bir tip, 24 satırda birden
fazla tip vardır. Bir satırdaki maksimum eşzamanlı etiket sayısı üçtür.

| Kombinasyon | Sayı |
|---|---:|
| NONE | 9.652 |
| TWF | 42 |
| HDF | 106 |
| PWF | 80 |
| OSF | 78 |
| RNF | 18 |
| TWF+OSF | 2 |
| TWF+RNF | 1 |
| HDF+PWF | 3 |
| HDF+OSF | 6 |
| PWF+OSF | 11 |
| TWF+PWF+OSF | 1 |

Pairwise sayımlar üçlü kombinasyonu her ilgili çifte dahil eder. Sıfırdan
büyük birliktelikler `TWF+PWF=1`, `TWF+OSF=3`, `TWF+RNF=1`,
`HDF+PWF=3`, `HDF+OSF=6` ve `PWF+OSF=12`'dir. Aynı satırda birden fazla
doğru hedef bulunması klasik multiclass varsayımını ihlal eder.

## 5. Machine failure tutarlılığı

| Grup | Sayı |
|---|---:|
| Machine failure=0, tip yok | 9.643 |
| Machine failure=1, en az bir tip var | 330 |
| Machine failure=1, tip yok | 9 |
| Machine failure=0, en az bir tip var | 18 |
| Multi-label ve Machine failure=1 | 24 |
| Multi-label ve Machine failure=0 | 0 |

Bu yapı otomatik etiket düzeltmesini haklı çıkarmaz. Tutarsızlıklar veri
kalitesi uyarısı olarak korunur.

## 6. RNF değerlendirmesi

RNF yalnız 19 pozitife sahiptir. Bunların 18'inde `Machine failure=0`, birinde
`Machine failure=1`'dir; bir RNF satırı TWF ile birliktedir. Mevcut binary split
RNF'yi train/validation/test içinde `15/3/1` dağıtmıştır. Validation'da üç,
testte bir pozitif üzerinden recall veya PR-AUC yorumlamak tek bir satırla büyük
oranda değişen, savunulamaz derecede kararsız bir sonuç üretir.

RNF belirli bir fiziksel failure mode değil, veri setine rastlantısal eklenen bir
etikettir. Bu nedenle beşinci multi-label hedef olarak eğitilmesi önerilmez.
RNF metadata ve veri kalitesi raporunda korunmalı, kullanıcıya model tahmini
olarak sunulmamalı ve görüldüğünde “belirsiz/rastlantısal arıza — genel teknik
inceleme” operasyonel politikasına yönlendirilmelidir.

## 7. Binary split dağılımı

Sprint 8'in seed 42 ve binary `Machine failure` stratified %70/%15/%15 split'i
aynen yeniden kullanılmıştır.

| Split | Satır | TWF | HDF | PWF | OSF | RNF | Multi-label | MF=1/tip yok | MF=0/tip var |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Train | 7.000 | 33 | 82 | 69 | 66 | 15 | 19 | 6 | 14 |
| Validation | 1.500 | 8 | 12 | 15 | 17 | 3 | 3 | 2 | 3 |
| Test | 1.500 | 5 | 21 | 11 | 15 | 1 | 2 | 1 | 1 |

Bütün satırlar ayrık splitlerde tam bir kez bulunur. Bununla birlikte binary
stratification yalnız ana hedef oranını korur; her tipin veya kombinasyonun
oranını korumaz. Örneğin TWF validation/test `8/5`, HDF ise `12/21` dağılır.
Gelecek sprintte iterative multilabel stratification faydalı olabilir; fakat yeni
bağımlılık, split sözleşmesi ve karşılaştırılabilirlik maliyeti ayrıca karara
bağlanmalıdır. Bu sprint mevcut split'i değiştirmez.

## 8. Leakage ve test kümesi sınırı

Etiket şemasını anlamak için tüm veri üzerinde yalnız toplu structural audit
yapılmıştır. Bu inceleme model, hiperparametre veya threshold seçimi değildir.
Test kümesi gelecek model seçimi için kilitli kalır.

- TWF/HDF/PWF/OSF/RNF yalnız hedeftir; feature olamaz.
- `Machine failure` failure-type modeline feature olarak verilmez. Aksi durum
  gerçek etiketi veya önceki model kararını input gibi kullanarak leakage ve
  serving mismatch yaratır.
- UDI, Product ID, sentetik `machine_id` ve `timestamp` feature değildir.
- Yalnız ürün tipi, sensörler ve ortak türetilmiş fiziksel feature'lar kullanılır.

## 9. Multiclass ve multi-label karşılaştırması

Klasik multiclass her satıra tek sınıf zorlar. Bu veri setinde 24 satır iki veya
üç fiziksel etiketi birlikte taşıdığından multiclass ya doğru etiketleri siler ya
da az destekli yapay kombinasyon sınıfları üretir. Multi-label ise her hedefi
ayrı bir 0/1 kararı olarak temsil eder; HDF ve PWF aynı anda 1 olabilir. `NONE`
ayrı bir sınıf değil, bütün modellenen hedeflerin 0 olmasıdır.

Binary relevance, her etiket için bağımsız binary model kurar.
`OneVsRestClassifier` bu düzeni tek estimator arayüzüyle uygular; etiketler arası
bağımlılığı doğrudan modellemez. Her etiket farklı prevalence ve hata maliyetine
sahip olduğundan tek global threshold yerine validation'da ayrı threshold gerekir.

Micro ortalama bütün etiket kararlarını bir havuzda toplar ve sık etiketlerin
etkisini büyütür. Macro her etikete eşit ağırlık verir; nadir etiket çöküşünü
gösterir. Weighted ortalama support ile ağırlıklandırır. Exact/subset accuracy,
bütün etiketlerin aynı anda kusursuz olmasını ister ve ana seçim metriği değildir.
Hamming loss yanlış etiket kararı oranını anlatır; yoğun negatifler nedeniyle
tek başına iyi görünebilir. Az pozitifli etiketlerde PR-AUC ve recall birkaç
örneğin yer değiştirmesiyle ciddi oynar; support ile birlikte yorumlanmalıdır.

## 10. Önerilen problem ve servis tanımı

Öneri hiyerarşik multi-label yapıdır:

1. Binary model tüm kayıtlarda `Machine failure` riskini hesaplar.
2. Operasyonel API akışında risk uyarısı varsa fiziksel tip modeli çağrılır.
3. Tip modeli TWF/HDF/PWF/OSF için birbirinden bağımsız olasılıklar üretir.
4. Birden fazla tip threshold'u geçebilir; hiçbiri geçmezse tip `NONE/belirsiz`
   olarak ele alınır, yapay bir tip atanmaz.
5. RNF model çıktısı değil operasyonel inceleme politikasıdır.

Gating binary modelin false negative'lerinin tip çıktısını bastırabileceği anlamına
gelir. Bu nedenle gelecek offline değerlendirmede tip modeli bütün uygun satırlarda
ayrıca ölçülmeli; servis zincirinin uçtan uca kaçırma oranı da raporlanmalıdır.

## 11. Gelecek deney planı

Yalnız iki kontrollü aday önerilir:

1. Her etiket için Logistic Regression binary-relevance baseline; `class_weight`
   yalnız train verisinde kontrollü aday olarak karşılaştırılır.
2. Random Forest tabanlı binary relevance/multi-output yaklaşımı; aynı feature,
   split ve seed ile karşılaştırılır.

Etiket bazında support, precision, recall, F1, PR-AUC, confusion matrix, FP ve FN;
toplu olarak micro precision/recall/F1, macro precision/recall/F1, weighted F1 ve
Hamming loss raporlanır. Exact/subset match yalnız yardımcı metriktir. Accuracy
ana seçim metriği değildir.

Önceden tanımlı seçim politikası: RNF hariç her etiket için validation support'u
ve tahmin çöküşü önce kontrol edilir; geçerli adaylar arasında en yüksek validation
macro PR-AUC seçilir. Etiket threshold'ları yalnız validation'da F1'i maksimize
eder; eşitlikte daha yüksek recall tercih edilir. Operasyonel false-negative
maliyeti için recall odaklı alternatif ayrı raporlanır, test kümesi hiçbir seçime
katılmaz. Minimum güvenilir support karşılanmıyorsa etiket için model yayınlanmaz.

## 12. Sentetik veri sınırı ve sunum cümlesi

AI4I sentetik bir veri setidir. Etiket birliktelikleri gerçek saha nedenselliği,
temporal genelleme veya farklı ekipmanlarda performans kanıtı değildir.

Sunumda kullanılabilecek kısa açıklama:

> AI4I verisinde 24 kayıt aynı anda birden fazla fiziksel arıza etiketi taşıdığı için problemi klasik multiclass yerine hiyerarşik multi-label olarak tanımladık. Rastlantısal RNF etiketi ise yalnız 19 örneğe sahip olması ve bunların 18'inde ana hedefle tutarsız olması nedeniyle model dışı operasyonel inceleme politikasına ayrıldı.
