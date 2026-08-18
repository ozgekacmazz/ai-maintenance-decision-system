# Bakım öncelik ve karar motoru

## İş problemi ve mimari

`maintenance-priority-1.0.0`, kalıcı tahmin snapshot'larını bakım kuyruğunda
karşılaştırılabilir, açıklanabilir bir karara dönüştüren saf ve deterministik kural
motorudur. İkinci bir ML modeli değildir: iş politikası görünür sabitlerde tutulur,
aynı girdiden aynı sonuç alınır ve her puan katkısı denetlenebilir. Motor DB veya
request nesnesi kullanmaz; canlı makine, parça ve stok verisini tekrar okumaz.

Teknik aciliyet ile tedarik riski ayrı tutulur. Böylece parça hazırlığı teknik riski
gizleyemez; uzun tedarik süresi de düşük model riskini yapay bir kritik arızaya
dönüştüremez.

## Formüller, ağırlıklar ve sınırlar

Teknik skorun katkıları şunlardır:

- `55 × risk_orani`
- `25 × (kritiklik_snapshot - 1) / 4`
- risk eşiği aşıldıysa `10`
- güvenilir HDF/PWF/OSF varsa `10`; riskli ve güvenilir tip yoksa belirsizlik için `5`
- eşik aşan deneysel TWF varsa sınırlı olarak `2`

Risk uyarısı yoksa teknik skor en fazla 39'dur. Tedarik skoru her parçanın riskini
hesaplar ve en yüksek skoru darboğaz kabul eder; eşitlik parça koduyla çözülür.
Sıralama değişikliği sonucu değiştirmez.

- Yeterli stok: bakım sonrası miktar minimum stok altındaysa 20, değilse 5.
- Yetersiz stok: `60 + 20 × eksik_orani + min(20, tedarik_gun / 30 × 20)`.
- `KAYIT_YOK`: stok sıfır sayılmaz; skor 55 ve ERP doğrulama aksiyonu üretir.
- ERP eşlemesi yok: tedarik skoru 0; teknik karar devam eder.

`nihai_oncelik = 0.80 × teknik_aciliyet + 0.20 × tedarik_riski` formülü uygulanır.
Bütün skorlar 0–100'e clamp edilir ve iki ondalığa yuvarlanır. Seviye aralıkları
`[0,25)=DUSUK`, `[25,50)=ORTA`, `[50,75)=YUKSEK`, `[75,100]=KRITIK` biçimindedir.

## Aksiyon, güven ve arıza tipi politikası

Ana aksiyon matrisi DUSUK için `IZLEMEYE_DEVAM`, ORTA için `PLANLI_KONTROL`,
YUKSEK için `ONCELIKLI_BAKIM_PLANLA`, KRITIK için
`ACIL_TEKNIK_DEGERLENDIRME` üretir. Riskli ve tipi belirsiz düşük/orta sonuçta
`TEKNIK_INCELEME` kullanılır. `KAYIT_YOK` için `STOK_VERISINI_DOGRULA`, gerçek
stok yetersizliği için `TEDARIK_SURECINI_BASLAT` destekleyici aksiyonudur.

Yalnız `guvenilir_aday=true` HDF/PWF/OSF ana tip olabilir. En düşük sıralama değeri,
eşitlikte kod belirleyicidir. TWF yalnız `YETERSIZ_DESTEK` deneysel sinyalidir; kesin
tip veya parçaya özgü karar üretmez. RNF motor girdisi, response veya snapshot'a
giremez. Güvenilir tip ve eksiksiz ERP bağlamı `YUKSEK`; riskli belirsizlik `ORTA`,
TWF veya eksik stok bağlamıyla `DUSUK`; diğer durumlar `ORTA` karar güveni üretir.

Gerekçe ve uyarı metinleri merkezi sabit şablonlardır; kullanıcı girdisi metne
eklenmez. Sıraları deterministiktir ve puan etkileri hesapla aynıdır. Motor otomatik
makine durdurma veya güvenlik garantisi vermez. Nihai operasyonel karar yetkili bakım
personeline aittir.

## Snapshot, idempotency ve geçiş

Karar, gerekçe, destekleyici aksiyon ve uyarılar ilişkisel immutable snapshot'lardır.
Skor, choice, sıra ve uniqueness DB constraint'leriyle korunur. ML/SHAP transaction
dışında çalışır; tahmin, ERP ve karar snapshot'ları aynı kısa transaction içinde
yazılır. Karar child hatası bütün oluşturmayı geri alır. Idempotent tekrarda mevcut
UUID ve karar aynen döner, motor tekrar çalışmaz. Eski kayıtlara veri migration ile
yapay karar üretilmez; liste ve detay bunlarda karar alanlarını güvenli `null` döndürür.

## API, filtreleme ve sıralama

Liste; `oncelik_seviyesi`, `ana_aksiyon`, `karar_guveni`,
`minimum_nihai_skor`, `maksimum_nihai_skor` filtrelerini kabul eder. `sirala` yalnız
`±nihai_oncelik`, `±olcum_zamani`, `±risk_orani`, `±makine_kritiklik` değerlerini
kabul eder. Varsayılan iş kuyruğu nihai skor azalan, teknik skor azalan, ölçüm zamanı
artan ve UUID sırasıdır. Pagination ve mevcut filtreler korunur.

## Örnek hesaplamalar

Risk 0.80, kritiklik 5, risk uyarısı ve güvenilir tip için teknik skor
`44 + 25 + 10 + 10 = 89` olur. Yeterli stok skoru 5 ise nihai skor
`89 × 0.8 + 5 × 0.2 = 72.2` ve seviye YUKSEK'tir. Aynı teknik durumda tam stok
eksikliği ve 30 gün tedarik, tedarik skorunu 100 ve nihai skoru 91.2 yapar.

## F12 kontrol listesi ve sınırlamalar

Düşük risk/izleme; yüksek risk + güvenilir tip + yeterli/yetersiz/kayıtsız stok;
belirsiz tip; yalnız TWF; idempotent 200; conflict 409; geçersiz filtre/sıralama 400;
liste/detail karar alanları ve trace ID kontrol edilir. Sistem AI4I sentetik veri ve
snapshot kalitesiyle sınırlıdır; iş emri, stok rezervasyonu, replay ve otomatik
durdurma bu sürümün kapsamı dışındadır.
