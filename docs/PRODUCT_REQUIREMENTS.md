# Ürün Gereksinimleri

## 1. Durum ve kaynak ayrımı

Bu belge Sprint 21 final hardening sonrası aktif ürün gereksinimlerini ve bilinçli kapsam sınırlarını tanımlar.

- **PDF zorunluluğu:** Resmî ödevde açıkça beklenen davranış veya ekran.
- **PDF önerisi:** Bağlayıcı olmayan teknoloji, veri veya örnek değer.
- **Proje kararı:** Ekibin PDF'yi ihlal etmeden kesinleştirdiği yaklaşım.
- **Kapsam dışı:** İlk teslimatta geliştirilmeyecek konu.

## 2. Ürün hedefi

Sistem sensör verisinden arıza olasılığı ve olası arıza türü üretir, tahmini açıklar ve operasyonel verilerle önceliklendirir. Sistem karar desteği sağlar; kullanıcı onayı olmadan iş emri oluşturmaz.

## 3. Roller ve erişim

### 3.1 PDF zorunlulukları

- **USER:** Risk listesi, makine detayı ve iş emirleri ekranlarına erişir; yetkisi varsa taslağı onaylar veya reddeder.
- **ADMIN:** USER yetkilerine ek olarak makine/stok, tahmin logu ve kullanıcı yönetimine erişir.
- Admin ekranları yalnız menüde gizlenmez; sunucu tarafında ADMIN rolü doğrulanır.

### 3.2 Proje kararları

- Teknik rol kodları `USER` ve `ADMIN` olacaktır.
- Self-service kullanıcı kaydı olmayacaktır.
- Kullanıcı oluşturma, parola yenileme ve pasife alma işlemlerini ADMIN yapacaktır.

## 4. Zorunlu ekranlar

### 4.1 Kullanıcı girişi

Kullanıcı adı ve parola alınır. Başarılı giriş rolüne uygun sayfalara yönlendirir; başarısız giriş yalın bir hata gösterir.

### 4.2 Risk listesi

Risk uyarıları genel önceliğe göre sıralanır. Her satırda en az makine, arıza türü, risk oranı ve 1–5 genel öncelik bulunur.

### 4.3 Makine detay ekranı

Ekranda risk oranı, olası arıza türü, ilk üç açıklama faktörü, önerilen aksiyon, gerekli parça, stok durumu, tedarik süresi ve öncelikler gösterilir. Onayla ve Reddet işlemleri bulunur.

### 4.4 İş emirleri

Yalnızca onay sonrası oluşturulan iş emirleri listelenir. Makine, aksiyon, parça, genel öncelik, durum ve tarih gösterilir.

### 4.5 Admin ekranları

- Makine kritikliği görüntülenir ve güncellenir.
- Parça stok adedi ve tedarik süresi görüntülenir ve güncellenir.
- Tahminler tarih, makine, risk, öncelik ve kullanıcı kararıyla görüntülenir.
- Kullanıcı oluşturulur, parolası yenilenir ve hesabı pasife alınır.

## 5. Tahmin ve açıklama

### 5.1 PDF zorunlulukları

- Kayıtlı model sensör girdisinden arıza olasılığı ve arıza türü üretir.
- Eşik üzerindeki sonuç risk uyarısı olur.
- Her tahmin için açıklama faktörleri saklanır ve kullanıcıya gösterilir.
- Uygulama çalışırken model eğitilmez.

### 5.2 Proje kararları

- İlk üç açıklama faktörü mutlak SHAP etkisine göre azalan sırada seçilir.
- Her faktör için feature adı, gözlenen değer, SHAP değeri ve etkinin yönü saklanır.
- Nihai threshold validation verisiyle belirlenir. `0.60` yalnız PDF önerisidir.
- Model joblib ile `.joblib` uzantılı, sürümlenmiş bir artefakta kaydedilir.

## 6. Önceliklendirme

PDF'nin zorunlu genel öncelik yaklaşımı korunur:

`ham_genel_oncelik = ariza_riski × makine_kritikligi × stok_katsayisi`

Ham değer, belgelenmiş ve test edilmiş eşiklerle 1–5 arasında bir tam sayıya dönüştürülür. Stok yokluğu ve tedarik süresi stok katsayısını yükseltebilir. Katsayı değerleri ve 1–5 dönüşüm eşikleri uygulama öncesinde veri analiziyle kesinleştirilecektir.

Proje kararı olarak:

- `bakim_onceligi`, risk ve makine kritikliğinin operasyonel etkisini açıklar.
- `tedarik_onceligi`, stok yokluğu ve tedarik süresinin etkisini açıklar.
- Bu alt skorlar genel önceliğin yerine geçmez ve kullanıcıya genel önceliğin gerekçesi olarak sunulur.

## 7. İş emri ve karar akışı

1. Tahmin ve risk uyarısı kaydedilir.
2. Sistem önerilen aksiyonla bir iş emri taslağı gösterir.
3. Kullanıcı onaylarsa iş emri oluşturulur.
4. Kullanıcı reddederse iş emri oluşturulmaz.
5. Her onay veya ret; karar türü, kullanıcı kimliği ve karar zamanı ile kaydedilir.
6. Aynı tahmin için birden fazla iş emri transaction ve benzersiz kısıtla engellenir.

## 8. Replay

Demo verisini kontrollü HTTP batch adımlarıyla sisteme veren replay akışı uygulanmıştır. Prepared verideki sentetik makine/zaman alanları audit bağlamında korunur; seçilen aktif DB makinesi inference hedefidir. Oluşturma ve adımlama idempotency/optimistic concurrency kurallarıyla duplicate sonucu engeller.

Replay model değerlendirmesinde ana metrikler precision, recall, PR-AUC ve confusion
matrix'tir; accuracy KPI olarak kullanılmaz. F1 yalnız yardımcı metriktir. Pozitif
sınıf arızadır. PR-AUC gerçek pozitif etiket ve risk olasılığı üzerinden hesaplanır;
tek sınıflı veya skoru eksik replay'de kullanılabilir değil olarak gösterilir.

## 9. Veri ve entegrasyon sınırı

- AI4I 2020 veri seti PDF önerisidir ve proje tarafından demo/replay için seçilmiştir.
- Sentetik `machine_id` ve `timestamp` yalnız demo/replay içindir.
- Gerçek ERP bağlantısı ilk sürüm kapsamı dışındadır.
- Makine, stok, parça, aksiyon ve iş emri yapıları ERP'ye hazır iç veri modeli ve API olarak uygulanmıştır.

## 10. Ek ürün özellikleri

PDF'yi bozmadan eklenen özellikler; karar snapshot'ı, model sürümü, threshold, SHAP etkileri, stok bağlamı, veri kalite kapısı, `trace_id` ve standart hata sözleşmesidir.

## Canonical genel öncelik ve legacy geçişi

Yeni bakım kararlarında canonical genel öncelik 1–5 aralığındadır. Hesap `risk_orani × makine_kritikligi × stok_katsayisi` biçimindedir; `stok_katsayisi = 1 + tedarik_riski_skoru / 100` olarak belirlenir. Ham sonuç aralıkları 0–2 → 1, >2–4 → 2, >4–6 → 3, >6–8 → 4 ve >8–10 → 5'tir.

Geçmiş karar ve iş emri kayıtlarının canonical alanları `NULL` kalabilir. Otomatik backfill yapılmaz, mevcut SLA tarihleri değiştirilmez ve eksik geçmiş veriden stok katsayısı üretilmez. Bu kayıtlar kullanıcı arayüzünde açıkça legacy öncelik olarak gösterilir.
