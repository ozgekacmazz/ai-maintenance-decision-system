# Bakım API'si

Tüm endpoint'ler JWT access token ister. USER yalnız aktif kayıtları okuyabilir; ADMIN aktif ve pasif kayıtları okuyabilir ve yazabilir. Django `is_staff`/`is_superuser` alanları ürün yetkisi sağlamaz.

| Kaynak | Liste / oluşturma | Detay / güncelleme | Aktiflik |
|---|---|---|---|
| Makine | `GET/POST /api/makineler/` | `GET/PATCH /api/makineler/{id}/` | `POST /api/makineler/{id}/aktiflik/` |
| Parça | `GET/POST /api/parcalar/` | `GET/PATCH /api/parcalar/{id}/` | `POST /api/parcalar/{id}/aktiflik/` |
| Stok | `GET/POST /api/stoklar/` | `GET/PATCH /api/stoklar/{id}/` | — |
| Arıza–parça kuralı | `GET/POST /api/ariza-parca-kurallari/` | `GET/PATCH /api/ariza-parca-kurallari/{id}/` | `POST /api/ariza-parca-kurallari/{id}/aktiflik/` |

| İşlem | USER | ADMIN |
|---|---:|---:|
| Aktif kayıtları okuma | Evet | Evet |
| Pasif kayıtları okuma | Hayır (404) | Evet |
| POST / PATCH / aktiflik | Hayır (403) | Evet |

Fiziksel DELETE sunulmaz. Makine, parça ve kurallar `{"aktif": false}` gövdeli aktiflik endpoint'iyle pasifleştirilir. Aynı durumun yeniden istenmesi başarılı ve idempotenttir. Stok modelinde aktiflik alanı yoktur; pasif parçanın stoku USER'a görünmez.

## İstek ve yanıt örneği

```json
POST /api/makineler/
{"kod":"MK-01","ad":"Pres","tip":"Hidrolik","kritiklik":4}
```

```json
{"id":1,"kod":"MK-01","ad":"Pres","tip":"Hidrolik","kritiklik":4,"aktif":true,"olusturulma_zamani":"...","guncellenme_zamani":"..."}
```

Listeler varsayılan 20, en fazla 100 kayıt döndürür. `sayfa` ve `sayfa_boyutu` kullanılır:

```json
{"count":25,"next":"...","previous":null,"results":[]}
```

## Filtreler

- Makine: `arama` (kod/ad/tip), `aktif`, `kritiklik`, `sirala` (`kod`, `ad`, `kritiklik` ve `-` önekli halleri).
- Parça: `arama` (kod/ad), `aktif`, `sirala` (`kod`, `ad` ve tersleri).
- Stok: `arama` (parça kodu/adı), `dusuk_stok`, `sirala` (`stok_adedi`, `tedarik_suresi_gun` ve tersleri).
- Kural: `arama`, `ariza_tipi`, `parca_id`, `aktif`, `sirala` (`ariza_tipi`, `parca_id` ve tersleri).

Geçersiz veya allowlist dışı değer 400 döner. USER'ın görünürlüğü filtrelerden önce aktif kayıtlarla sınırlandırılır.

## Bütünlük ve hata davranışı

- Kodlar trim edilir; boş kod/ad, 1–5 dışı kritiklik ve negatif stok değerleri 400'dür.
- Yinelenen makine/parça kodu, parça başına ikinci stok, aynı arıza–parça çifti ve aynı türde ikinci parçasız kural 409'dur.
- Pasif parçaya stok veya aktif kural bağlanamaz (400). Olmayan `parca_id` 400'dür.
- 401 kimlik doğrulama eksikliğini, 403 rol yetersizliğini, 404 bulunamayan ya da USER'dan gizlenen kaydı belirtir.
- PostgreSQL hata ayrıntıları yanıtlanmaz. Hatalar [standart hata sözleşmesini](ERROR_CONTRACT.md) kullanır; gövdedeki `trace_id`, `X-Trace-ID` başlığıyla aynıdır.

Stok değeri hareket değil güncel snapshot'tır; PATCH istemcinin verdiği nihai değeri yazar. Oluşturma/güncelleme işlemleri transaction içindedir ve stok güncellemesi eşzamanlı yazmaları sıralamak için `SELECT ... FOR UPDATE` satır kilidi kullanır.

