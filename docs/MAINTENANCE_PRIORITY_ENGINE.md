# Bakım öncelik ve karar motoru

Bu belge güncel karar sözleşmesini tanımlar. Motor ikinci bir ML modeli değil; model çıktısını, makine kritikliğini ve snapshot alınmış stok/tedarik bağlamını denetlenebilir bir iş kararına dönüştüren saf ve deterministik politikadır.

## Model çıktısı ile iş kuralının ayrımı

Binary model `risk_orani` ve `risk_uyarisi`; fiziksel modeller HDF/PWF/OSF/TWF sinyalleri üretir. RNF model çıktısı değildir. Legacy karar motoru teknik aciliyet, tedarik riski, 0–100 `nihai_oncelik_skoru`, dört seviyeli açıklama etiketi, aksiyon ve güven gerekçelerini üretmeye devam eder. Bunlar canonical genel önceliğin yerine kullanılmaz.

## Canonical 1–5 genel öncelik

Formül sürümü `general-priority-1.0.0`:

```text
stok_katsayisi = 1 + tedarik_riski_skoru / 100
ham_genel_oncelik = risk_orani × makine_kritikligi × stok_katsayisi
```

`risk_orani` 0–1, `makine_kritikligi` 1–5 ve `tedarik_riski_skoru` 0–100 aralığındadır. Hesap `Decimal` ile yapılır; stok katsayısı ve ham değer dört ondalığa `ROUND_HALF_UP` ile quantize edilir.

| Ham değer | Genel öncelik |
|---:|---:|
| 0–2 | 1 |
| >2–4 | 2 |
| >4–6 | 3 |
| >6–8 | 4 |
| >8–10 | 5 |

Yeni kalıcı tahminde `genel_oncelik`, `stok_katsayisi`, `ham_genel_oncelik` ve formül sürümü aynı immutable `BakimKarariSnapshot` içine yazılır. Dört alan birlikte dolu veya birlikte `NULL` olmalıdır. Legacy snapshot'lara yapay backfill uygulanmaz; API bunları güvenli null canonical alanlarla gösterebilir.

## Legacy açıklama motoru

Teknik skor; risk, makine kritiklik snapshot'ı, risk uyarısı ve güvenilir fiziksel sinyallerden oluşur. Tedarik skoru stok yeterliliği, eksik oranı ve tedarik süresini değerlendirir. Legacy nihai skor:

```text
nihai_oncelik_skoru = 0.80 × teknik_aciliyet_skoru + 0.20 × tedarik_riski_skoru
```

Legacy 0–100 değer ve `DUSUK/ORTA/YUKSEK/KRITIK` etiketi açıklanabilirlik ve geriye uyumluluk için korunur. UI sıralama/rozet sözleşmesinin canonical kaynağı 1–5 genel önceliktir.

Yalnız güvenilir HDF/PWF/OSF ana fiziksel tip olabilir. TWF deneysel/yetersiz destekli sinyaldir; RNF inference veya karar girdisi değildir. Stok kaydı yokluğu sıfır stok sayılmaz; doğrulama aksiyonu üretir. Motor otomatik makine durdurmaz ve güvenlik garantisi vermez.

## İş emri, override ve SLA

İş emri snapshot'tan immutable `kaynak_genel_oncelik` değerini alır; `etkin_genel_oncelik` başlangıçta buna eşittir. ADMIN override yalnız etkin değeri değiştirir. Önceki/yeni değer, aktör, neden, trace ID ve version immutable iş emri olayında saklanır.

SLA politika sürümü `general-priority-sla-1.0.0`:

| Etkin öncelik | Müdahale süresi |
|---:|---:|
| 1 | 168 saat |
| 2 | 120 saat |
| 3 | 72 saat |
| 4 | 24 saat |
| 5 | 4 saat |

Override deadline'ı override anından itibaren yeniden hesaplar. Kaynak karar değişmez. Canonical alanı olmayan legacy iş emirleri eski dört seviyeli `work-order-policy-1.0.0` SLA davranışını sürdürür; geçmiş deadline ve idempotent sonuçlar backfill edilmez.

## Snapshot, transaction ve API

ML/SHAP transaction dışında çalışır; tahmin, ERP ve karar snapshot'ları kısa transaction içinde atomik yazılır. Child kayıt hatası bütün create işlemini geri alır. Idempotent tekrarda mevcut UUID/snapshot döner ve motor yeniden çalışmaz.

Tahmin listesi `genel_oncelik` filtresi ile `genel_oncelik`/`-genel_oncelik` sıralamasını destekler. ADMIN Tahmin Logları canonical önceliği ve kullanıcı karar durumunu gösterir. İş emri filtreleri kaynak/etkin önceliği ayırır.

## Sınırlamalar

Karar, model ve snapshot kalitesiyle sınırlıdır. Stok rezervasyonu, satın alma, bildirim ve otomatik durdurma üretmez. Nihai operasyonel yetki kullanıcıdadır; replay tahminleri operasyon kuyruğunda iş emrine dönüştürülemez.
