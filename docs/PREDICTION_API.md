# Sprint 12 Hiyerarşik Risk Tahmin API'si

## Endpoint

`POST /api/tahminler/risk/` aktif `USER` ve `ADMIN` kullanıcıları için JWT ile
korunur. İstek yalnız aşağıdaki ham sensör alanlarını kabul eder:

```json
{
  "urun_tipi": "L",
  "hava_sicakligi_k": 298.1,
  "proses_sicakligi_k": 308.6,
  "donus_hizi_rpm": 1551,
  "tork_nm": 42.8,
  "takim_asinmasi_dk": 0
}
```

Türetilmiş özellikler sunucuda hesaplanır. Hedef, leakage, kimlik, timestamp ve
diğer bilinmeyen alanlar `400` ile reddedilir. Sayısal değerler boolean, NaN veya
sonsuz olamaz; sıcaklık ve dönüş hızı pozitif, tork ve takım aşınması negatif
olmamalıdır.

## Başarılı yanıtlar

### Risk eşik altında

Failure-type modeli çalıştırılmadığı için bu durumda onun model ve pipeline sürümü
response'a eklenmez.

```json
{
  "risk_orani": 0.12,
  "risk_uyarisi": false,
  "threshold": 0.22958333333333336,
  "model_version": "binary-failure-1.0.0",
  "pipeline_version": "1.0.0",
  "ariza_tipi_degerlendirmesi": {
    "durum": "RISK_ESIK_ALTINDA",
    "guvenilir_adaylar": [],
    "deneysel_sinyaller": [],
    "belirsiz_fiziksel_tip": false
  }
}
```

### Değerlendirildi ve güvenilir aday bulundu

```json
{
  "risk_orani": 0.7842,
  "risk_uyarisi": true,
  "threshold": 0.22958333333333336,
  "model_version": "binary-failure-1.0.0",
  "pipeline_version": "1.0.0",
  "ariza_tipi_degerlendirmesi": {
    "durum": "DEGERLENDIRILDI",
    "model_version": "failure-type-1.0.0",
    "pipeline_version": "1.0.0",
    "guvenilir_adaylar": [
      {"kod": "PWF", "olasilik": 0.91, "threshold": 0.29512499999999997}
    ],
    "deneysel_sinyaller": [
      {
        "kod": "TWF",
        "olasilik": 0.18,
        "threshold": 0.051,
        "esik_asildi": true,
        "guven_durumu": "YETERSIZ_DESTEK",
        "operasyonel_kullanima_uygun": false
      }
    ],
    "belirsiz_fiziksel_tip": false
  }
}
```

### Değerlendirildi, güvenilir aday bulunamadı ve TWF sinyali var

```json
{
  "risk_orani": 0.7842,
  "risk_uyarisi": true,
  "threshold": 0.22958333333333336,
  "model_version": "binary-failure-1.0.0",
  "pipeline_version": "1.0.0",
  "ariza_tipi_degerlendirmesi": {
    "durum": "DEGERLENDIRILDI",
    "model_version": "failure-type-1.0.0",
    "pipeline_version": "1.0.0",
    "guvenilir_adaylar": [],
    "deneysel_sinyaller": [
      {
        "kod": "TWF",
        "olasilik": 0.18,
        "threshold": 0.051,
        "esik_asildi": true,
        "guven_durumu": "YETERSIZ_DESTEK",
        "operasyonel_kullanima_uygun": false
      }
    ],
    "belirsiz_fiziksel_tip": true
  }
}
```

Yalnız TWF sinyalinin eşik aşması, güvenilir fiziksel tip bulunduğu anlamına
gelmez.

`risk_orani`, pozitif `Machine failure` sınıfının `predict_proba` çıktısıdır.
`risk_uyarisi`, metadata'dan okunan threshold ile `risk_orani >= threshold`
karşılaştırmasıdır. Yanıt artefakt yolu veya checksum içermez ve her yanıtta
`X-Trace-ID` header'ı bulunur.

## Sprint 14 açıklanabilirlik alanları

Düşük risk yanıtında `aciklanabilirlik.durum=RISK_ESIK_ALTINDA` ve
`risk_aciklamasi=null` olur. Riskli yanıtta durum `ACIKLANDI` olur ve binary
`risk_aciklamasi` ilk üç etkiyi taşır. Threshold aşan güvenilir aday ile threshold
aşan deneysel TWF öğesine kendi `aciklama` alanı eklenir; aşmayan tipler açıklanmaz.
Mevcut üst seviye alanlar silinmez. Alanlar, cache ve F12 kontrolleri
[SHAP API entegrasyon belgesinde](SHAP_API_INTEGRATION.md) açıklanır.

## Hatalar

- Geçersiz alan: `400 GECERSIZ_ISTEK`
- Anonim istek: `401 KIMLIK_DOGRULAMA_GEREKLI`
- Pasif/yetkisiz kullanıcı: `403 YETKI_YETERSIZ`
- Eksik/bozuk metadata veya artefakt, checksum/sürüm/feature/sınıf uyuşmazlığı
  ya da inference hatası: `503 MODEL_HIZMETI_KULLANILAMIYOR`

Hatalar merkezi `hata` sözleşmesini kullanır. Gövdedeki `trace_id`, response
header'ındaki `X-Trace-ID` ile aynıdır; dosya yolu, checksum, exception veya stack
trace istemciye açıklanmaz.

## Yapılandırma

`MODEL_ARTIFACT_PATH`, `MODEL_METADATA_PATH`, `FAILURE_TYPE_MODEL_ARTIFACT_PATH`
ve `FAILURE_TYPE_MODEL_METADATA_PATH` güvenilir yerel dosyaları gösterir.
Model ilk istekte yüklenir ve process belleğinde tutulur. Artefakt yoksa uygulama
başlatılır; tahmin endpoint'i kontrollü `503` verir. Dağılım dışı/drift uyarıları
bu sprint kapsamında değildir.

Risk eşik altında `ariza_tipi_degerlendirmesi.durum=RISK_ESIK_ALTINDA` olur ve
failure-type modeli yüklenmez. Riskli kayıtta model kullanılamazsa standart `503`
döner. HDF/PWF/OSF yalnız threshold aşınca güvenilir adaydır; TWF her riskli
değerlendirmede yetersiz destekli deneysel sinyal olarak gösterilir. RNF response'a
girmez. Ayrıntılar [hiyerarşik akış belgesindedir](HIERARCHICAL_PREDICTION_FLOW.md).

## Kalıcı kayıt kaynağı

Makineye bağlı audit kaydı için `POST/GET /api/tahminler/kayitlar/` ve
`GET /api/tahminler/kayitlar/{uuid}/` kullanılır. İstek, idempotency, filtre,
snapshot ve hata sözleşmeleri [kalıcı tahmin kayıtları belgesindedir](PREDICTION_RECORDS.md).
Yeni kayıtlardaki açıklanabilir bakım kararı, formüller, aksiyonlar ve iş kuyruğu
sıralaması [bakım öncelik motoru belgesinde](MAINTENANCE_PRIORITY_ENGINE.md) tanımlıdır.
Kararı operasyonel iş emrine dönüştüren endpointler ve audit sözleşmesi
[iş emri yaşam döngüsü belgesinde](WORK_ORDER_WORKFLOW.md) açıklanır.

Örnek karar bölümü:

```json
{
  "bakim_karari": {
    "motor_surumu": "maintenance-priority-1.0.0",
    "teknik_aciliyet_skoru": 89.0,
    "tedarik_riski_skoru": 5.0,
    "nihai_oncelik_skoru": 72.2,
    "oncelik_seviyesi": "YUKSEK",
    "ana_aksiyon": "ONCELIKLI_BAKIM_PLANLA",
    "destekleyici_aksiyonlar": [],
    "ana_ariza_tipi": "HDF",
    "karar_guveni": "YUKSEK",
    "gerekceler": [
      {
        "kod": "MODEL_RISKI",
        "mesaj": "Model risk olasılığı teknik aciliyete katkı sağladı.",
        "etki": "ARTIRDI",
        "puan_etkisi": 44.0
      }
    ],
    "uyarilar": [
      {
        "kod": "INSAN_ONAYI_GEREKLI",
        "mesaj": "Nihai operasyonel karar yetkili bakım personeline aittir."
      }
    ],
    "olusturulma_zamani": "2026-08-18T10:00:00Z"
  }
}
```

Karar motoru hatası iç ayrıntı sızdırmadan `503
KARAR_MOTORU_KULLANILAMIYOR` döner; transaction'da hiçbir snapshot bırakılmaz ve
body `trace_id` ile `X-Trace-ID` eşleşir.
