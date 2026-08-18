# Terim Sözlüğü

## 1. Amaç

Bu sözlük kullanıcı arayüzündeki doğal Türkçe ile teknik identifierların tutarlı kullanılmasını sağlar. Markdown açıklamalarında doğal Türkçe kullanılır; kod, veritabanı identifierları ve kararlı teknik kodlar Türkçe-ASCII kurallarına uyar.

## 2. Ürün terimleri

| Türkçe terim | Teknik karşılık | Açıklama |
|---|---|---|
| arıza riski | `ariza_riski` | Modelin arıza olasılığı |
| arıza türü | `ariza_tipi` | TWF, HDF, PWF, OSF veya RNF |
| risk uyarısı | `risk_uyarisi` | Eşik üzerindeki tahmin |
| genel öncelik | `genel_oncelik` | 1–5 arasındaki kanonik sıralama değeri |
| bakım önceliği | `bakim_onceligi` | Genel önceliği açıklayan bakım alt skoru |
| tedarik önceliği | `tedarik_onceligi` | Genel önceliği açıklayan stok/tedarik alt skoru |
| stok katsayısı | `stok_katsayisi` | Stok ve tedarik etkisini genel önceliğe taşır |
| iş emri taslağı | `is_emri_taslagi` | Kullanıcı kararına sunulan, henüz iş emri olmayan öneri |
| iş emri | `is_emri` | Yalnız kullanıcı onayından sonra oluşan kayıt |
| karar türü | `karar_tipi` | `ONAY` veya `RET` |
| karar veren kullanıcı | `karar_veren_user_id` | Onay veya ret işlemini yapan kullanıcı |
| açıklama faktörü | `aciklama_faktoru` | SHAP etkisiyle sıralanan feature |
| model artefaktı | `model_artefakti` | Joblib ile kaydedilmiş `.joblib` dosyası |
| replay | `replay` | Demo satırlarını sisteme sırayla gönderen akış |

## 3. Roller

- `USER`: Operasyonel ekranlara erişen kullanıcı.
- `ADMIN`: USER yetkilerine ek olarak yönetim ekranlarına erişen kullanıcı.

Rol kodları kararlı teknik değerlerdir ve büyük harfle yazılır.

## 4. Arıza kodları

- `TWF`: takım aşınması arızası
- `HDF`: ısı dağılımı arızası
- `PWF`: güç arızası
- `OSF`: aşırı zorlanma arızası
- `RNF`: rastgele arıza

RNF veri analizinde korunur. Güvenilir parça eşlemesi yoksa genel teknik inceleme aksiyonu kullanılır.

## 5. İsimlendirme politikası

- Veritabanı tablo ve kolon adları Türkçe-ASCII ve `snake_case` olur.
- Python değişkenleri ve alanları `snake_case`, sınıfları `PascalCase` olur.
- API hata kodları Türkçe-ASCII ve büyük harfli olur.
- Kullanıcı mesajları ve Markdown açıklamaları doğru Türkçe karakterlerle yazılır.
- Yerleşik kütüphane ve standart adları gereksiz yere Türkçeleştirilmez.

Doğru örnekler: `is_emirleri`, `genel_oncelik`, `karar_zamani`, `makine_kritikligi`.
