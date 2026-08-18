# Denetlenebilir bakım iş emri yaşam döngüsü

## İş problemi ve domain ayrımı

İş emri, immutable tahmin ve bakım kararı snapshot'ını operasyonel çalışmaya bağlayan
kontrollü güncellenebilir aggregate'tır. Tahmin, SHAP, ERP ve karar verileri iş emri
değişirken güncellenmez. İş emrinin güncel durumu değişebilir; her başarılı değişiklik
ayrı bir immutable `IsEmriOlayi` üretir.

İş emri otomatik makine durdurma veya güvenlik garantisi değildir. Stok azaltmaz,
rezervasyon veya satın alma siparişi oluşturmaz. Nihai operasyonel yetki bakım
personelindedir.
Replay kaynaklı tahminler sentetik/geçmiş değerlendirme akışıdır ve operasyon
kuyruğunu kirletmemek için iş emrine dönüştürülemez.

## Model şeması ve aktif emir politikası

`BakimIsEmri` UUID teknik kimliği ile `WO-{yıl}-{UUID ilk 12 hex}` insan referansını
birlikte saklar. Referans `max+1` kullanmaz, yarıştan etkilenmez ve güvenlik kimliği
değildir. Tahmin, makine, oluşturan ve atanan kullanıcı ilişkileri `PROTECT` kullanır.

Bir tahmin için `ACIK`, `ATANDI`, `DEVAM_EDIYOR` veya `BEKLEMEDE` durumlarında en
fazla bir emir PostgreSQL partial unique constraint ile korunur. Tamamlanan veya iptal
edilen emrin ardından aynı tahmin için yeni emir kontrollü biçimde açılabilir. Karar
snapshot'ı olmayan legacy tahminde karar yeniden hesaplanmaz ve
`409 IS_EMRI_KARARI_BULUNAMADI` döner.

## Durum makinesi

| Mevcut | İzin verilen hedefler |
|---|---|
| ACIK | ATANDI, IPTAL_EDILDI |
| ATANDI | DEVAM_EDIYOR, BEKLEMEDE, IPTAL_EDILDI |
| DEVAM_EDIYOR | BEKLEMEDE, TAMAMLANDI, IPTAL_EDILDI |
| BEKLEMEDE | ATANDI, DEVAM_EDIYOR, IPTAL_EDILDI |
| TAMAMLANDI | Yok |
| IPTAL_EDILDI | Yok |

Aynı duruma geçiş ve terminal durumdan çıkış reddedilir. `ATANDI` ve
`DEVAM_EDIYOR` için aktif atanmış kullanıcı; `BEKLEMEDE` için neden;
`TAMAMLANDI` için tamamlama notu; `IPTAL_EDILDI` için iptal nedeni zorunludur.
Başlangıç, tamamlama ve iptal zamanları server-side üretilir. İlk gerçek başlangıç
zamanı bekleme/devam döngüsünde korunur.

## Rol ve yetki matrisi

| İşlem | USER | ADMIN |
|---|---:|---:|
| Oluşturma ve okuma | Evet | Evet |
| Atama/yeniden atama | Hayır | Evet |
| Atanmış emirde operasyonel geçiş | Evet | Evet |
| Başkasının emrinde geçiş | Hayır | Evet |
| İptal | Hayır | Evet |
| Öncelik override | Hayır | Evet |

Aktif USER veya ADMIN atanabilir; hayali teknisyen rolü eklenmemiştir. ADMIN kendine
atama yapabilir. Pasif kullanıcı atanamaz.

## Idempotency, version ve locking

Create idempotency kapsamı `(olusturan, idempotency_key)`'dir. Fingerprint tahmin
UUID'si ile trim edilmiş başlık/açıklamanın sıralı kanonik JSON SHA-256 değeridir ve
response'a çıkmaz. İlk istek `201`; aynı key/payload `200` ve aynı UUID; farklı
payload `409 IDEMPOTENCY_CAKISMASI` üretir. Farklı key ile aynı aktif tahmin
`409 IS_EMRI_AKTIF_KAYIT_MEVCUT` sonucudur.

Atama, geçiş ve override isteklerinde `beklenen_version` zorunludur. Her işlem kısa
`transaction.atomic()` içinde `select_for_update()` ile kilitler. Uyuşmazlık
`409 ESZAMANLI_GUNCELLEME_CAKISMASI` üretir. Başarılı işlem version'ı tam bir artırır
ve aynı version numaralı tek olay yazar; olay hatası aggregate değişikliğini geri alır.

## SLA, gecikme ve override

Politika sürümü `work-order-policy-1.0.0`:

- KRITIK: 4 saat
- YUKSEK: 24 saat
- ORTA: 72 saat
- DUSUK: 168 saat

Deadline, server-side iş emri oluşturma zamanından hesaplanır ve timezone-aware'dir.
Override sonrası yeni deadline, override anından yeni etkin seviyenin SLA'sı ile
hesaplanır. Kaynak karar skoru/seviyesi değişmez. Override nedeni, önceki/yeni seviye,
actor, trace ve version olayda saklanır.

`gecikmis`, terminal olmayan emirlerde `now > hedef_mudahale_zamani` olarak sorgu ve
response sırasında hesaplanır; DB'de bayatlayan boolean tutulmaz. Tam deadline anı
gecikmiş sayılmaz.

## API

```text
POST /api/bakim/is-emirleri/
GET  /api/bakim/is-emirleri/
GET  /api/bakim/is-emirleri/{uuid}/
POST /api/bakim/is-emirleri/{uuid}/ata/
POST /api/bakim/is-emirleri/{uuid}/durum-gecisi/
POST /api/bakim/is-emirleri/{uuid}/oncelik-override/
```

Create örneği:

```json
{
  "tahmin_kaydi_id": "5de89a80-a5ba-48a8-81fb-1f19f7ce3d00",
  "idempotency_key": "client-work-order-17",
  "baslik": "A-17 öncelikli bakım incelemesi",
  "aciklama": "Model kararı sonrasında saha kontrolü planlandı."
}
```

Atama ve geçiş örnekleri:

```json
{"atanan_kullanici_id": 12, "beklenen_version": 1, "not": "Mekanik ekip"}
```

```json
{"beklenen_version": 2, "hedef_durum": "DEVAM_EDIYOR", "neden": "Saha kontrolüne başlandı."}
```

## Filtre, ordering ve performans

Durum, kaynak/etkin öncelik, makine, atanan, oluşturan, gecikme, override, oluşturma
ve deadline aralığı, ana tip ve tam iş emri numarası filtrelenebilir. Ordering allowlist:
`±etkin_oncelik`, `±hedef_mudahale_zamani`, `±olusturulma_zamani`,
`±guncellenme_zamani`, `±makine_kritiklik`, `±kaynak_nihai_skor`, `±durum`.

Varsayılan kuyruk terminal olmayan, gecikmiş, KRITIK→YUKSEK→ORTA→DUSUK, erken
deadline, eski oluşturma ve UUID sırasıdır. Liste en fazla 4, detay en fazla 5 sorguyla
test edilmiştir. Unknown query parametreleri reddedilir; pagination korunur.

## Hata kodları ve audit

- `IS_EMRI_AKTIF_KAYIT_MEVCUT`
- `IS_EMRI_GECISI_GECERSIZ`
- `IS_EMRI_KARARI_BULUNAMADI`
- `ESZAMANLI_GUNCELLEME_CAKISMASI`
- `IDEMPOTENCY_CAKISMASI`

Olaylar instance ve QuerySet üzerinden değiştirilemez/silinemez. Admin iş emri ve
olayları salt okunur gösterir; state machine admin formuyla bypass edilemez. Hatalar
SQL, constraint, traceback veya fingerprint sızdırmaz; body trace ID ile
`X-Trace-ID` eşleşir.

## F12 kontrol listesi ve sınırlamalar

Create, idempotent tekrar, atama, başlatma, bekleme, devam, tamamlama, büyüyen olay
geçmişi, stale version 409, yetkisiz USER 403, ADMIN override, gecikme filtresi,
terminal geçiş reddi ve trace ID izlenir. Bildirim, replay, frontend, iş gücü/ekip
takvimi, stok rezervasyonu ve otomatik satın alma bu sürümün kapsamı dışındadır.
