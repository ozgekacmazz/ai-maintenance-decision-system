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
