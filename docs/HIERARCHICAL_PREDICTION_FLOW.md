# Hiyerarşik risk ve fiziksel arıza tipi akışı

## Akış ve sorumluluklar

JWT ile doğrulanan `POST /api/tahminler/risk/` isteğinde sensör alanları bir kez
DataFrame'e çevrilir ve ortak `bakim_ml` feature engineering uygulanır. Binary
model önce çalışır; düşük riskli kayıtlarda gereksiz tip çıkarımını ve yanlış
operasyonel önerileri önlemek için failure-type modeli yalnız
`risk_uyarisi=true` olduğunda çalışır. İki model aynı dokuz alanlı feature
frame'ini kullanır.

Binary ve failure-type artefaktları ayrı tracked metadata, SHA-256, sözleşme
doğrulaması, kilit ve lazy cache ile yönetilir. Checksum joblib deserialization
öncesinde kontrol edilir. Yol değişikliği yalnız ilgili cache'i geçersiz kılar;
başarısız yükleme cache'e yazılmaz. Model dosyaları Git ve image dışında, Docker
mount'larında salt okunur tutulur.

## Serving politikası

- HDF, PWF ve OSF threshold aşınca olasılığa göre azalan operasyonel adaydır.
- Eşit olasılıkta merkezi sıra HDF, PWF, OSF'tir.
- TWF düşük test desteği ve zayıf precision nedeniyle her riskli değerlendirmede
  `YETERSIZ_DESTEK` deneysel sinyali olarak gösterilir; operasyonel aday değildir.
- RNF öğrenilmiş model çıktısı değildir ve response'ta probability/threshold almaz.
- Güvenilir aday yoksa, TWF aşılmış olsa bile `belirsiz_fiziksel_tip=true` olur.
  Bu bir RNF tahmini veya model hatası değil, modellenen güvenilir fiziksel
  nedenlerle eşleşmeme durumudur.

Çıktılar insan denetimli karar desteğidir. Otomatik makine durdurma, bakım emri
veya saha garantisi sağlamaz. AI4I sentetik, tip support'ları düşüktür ve binary
gating false-negative bir kaydın tip değerlendirmesini engelleyebilir.

## Hata davranışı

Risk eşik altındaysa failure-type artefaktına ihtiyaç yoktur. Risk eşik üstünde
metadata/artefakt eksikliği, checksum veya sözleşme uyuşmazlığı ve inference
hatası eksik bir `200` yerine `503 MODEL_HIZMETI_KULLANILAMIYOR` üretir. Standart
hata gövdesi ile `X-Trace-ID` eşleşir; yol, checksum ve traceback sızdırılmaz.

## Response sözleşmesi

Binary üst seviye alanları korunur. `ariza_tipi_degerlendirmesi`, düşük riskte
`RISK_ESIK_ALTINDA`; riskli ve başarılı tip çıkarımında `DEGERLENDIRILDI` döner.
Güvenilir adaylarda `kod`, `olasilik`, `threshold`; TWF sinyalinde bunlara ek
olarak `esik_asildi`, `guven_durumu` ve `operasyonel_kullanima_uygun` bulunur.
Olasılıklar `[0,1]` float değerleridir.

## F12 kontrol listesi

- Request payload ve `Authorization: Bearer` access token
- `200`, `400`, `401`, `503` durumları
- `X-Trace-ID` ve hata gövdesindeki trace ID
- `risk_orani`, `risk_uyarisi`
- `ariza_tipi_degerlendirmesi.durum`
- `guvenilir_adaylar` sırası ve alanları
- TWF `YETERSIZ_DESTEK` ve operasyonel kullanıma uygun olmama alanları
- RNF'nin response'ta bulunmaması
- İstek süresi ve response boyutu

Frontend ekranı, tahmin kaydı, SHAP, öncelik, replay ve iş emri bu sprintin
kapsamında değildir.

## Yerel HTTP smoke sonucu

İki gerçek yerel artefaktla JWT korumalı endpoint doğrulandı: düşük riskli sensör
girdisi `200/RISK_ESIK_ALTINDA`, yüksek riskli girdi `200/DEGERLENDIRILDI` ve iki
güvenilir aday döndürdü. TWF yetersiz destekli/operasyonel olmayan sinyaldi ve RNF
response'ta yoktu. Negatif tork `400`, anonim istek `401` aldı. Failure-type
artefaktı geçici olarak erişilemezken düşük riskli istek `200`, riskli istek
`503 MODEL_HIZMETI_KULLANILAMIYOR` aldı. Bu `503` için header, hata gövdesi ve
güvenli log trace ID değerleri eşleşti. Test kullanıcısı silindi ve artefakt
yerine geri kondu; token veya parola kaydedilmedi.
