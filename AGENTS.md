# AGENTS.md

## Amaç

Bu depo, proje genelinde güvenli ve sprint kontrollü çalışma için kalıcı talimatlar sunar. Bu belge yalnızca Sprint 0 için değil, projenin bütün sprintleri için geçerlidir.

## Her görev öncesi kontrol

- Deponun kök dizinindeki mevcut dosya yapısını, Git durumunu ve olası kullanıcı değişikliklerini incele.
- `git status --short --branch` ve `git remote -v` komutlarını salt okunur şekilde çalıştır.
- Kullanıcının mevcut değişikliklerini koru; ilgisiz dosyaları düzenleme, silme, stage etme veya commit etme.
- Yalnızca kullanıcının mevcut görevde açıkça belirttiği sprint kapsamında çalış.
- Kullanıcı onayı olmadan sonraki sprinte geçme.

## Yapılacaklar ve yasaklar

- Yeni bağımlılıkları yalnızca mevcut sprint için gerekli, gerekçelendirilmiş ve kullanıcı tarafından istenen kapsamda ekle. Eklenen her bağımlılığı görev sonunda raporla.
- Kullanıcı açıkça istemedikçe GitHub ayarlarını, remote yapılandırmasını veya branch yapısını değiştirme.
- Django, React, Node.js veya Python uygulama kodunu yalnızca mevcut sprint kapsamında açıkça isteniyorsa oluştur veya değiştir.
- `requirements.txt`, `package.json`, `Dockerfile` ve Docker Compose dosyalarını yalnızca mevcut sprint kapsamında açıkça gerekli ve istenmişse oluştur.
- Model eğitimi veya veri indirme işlemini yalnızca mevcut sprint kapsamında açıkça isteniyorsa gerçekleştir.
- Kullanıcı açıkça istemedikçe commit veya push yapma; branch silme, geçmişi yeniden yazma ya da benzeri depo yapısı değişiklikleri gerçekleştirme.
- `git reset --hard`, `git clean -fd`, `git checkout --` ve benzeri veri kaybına yol açabilecek yıkıcı komutları açık kullanıcı talebi olmadan kullanma.
- Çalıştırılmamış, başarısız olmuş veya eksik kalmış testleri başarılı olarak raporlama.

## Git ve dosya kuralları

- Depo dışındaki dosyalara müdahale etme.
- Gerçek PDF'leri, ham verileri, kişisel verileri veya özel kurum verilerini depoya kopyalama.
- Gizli bilgileri, parolaları veya tokenları depoya ekleme.
- `.env` ve yerel ortam dosyalarını Git kapsamında saklama.
- `data/raw` içindeki gerçek veri kümesi dosyalarını Git'e ekleme.
- `.gitkeep` dosyasının izlenmesine izin ver.

## Raporlama

Görev sonunda şu bilgileri raporla:

- Değişen dosyalar ve kısa gerekçeleri.
- Çalıştırılan doğrulama ve test komutları.
- Her komutun gerçek sonucu.
- Çalıştırılamayan, başarısız olan veya eksik kalan testler.
- Açık riskler.
- Git durumunun özeti.

## Hata ve güvenlik

- Düz metin gizli bilgileri, parolaları veya tokenları asla günlüklere yazma, yanıtta gösterme veya dosyaya kaydetme.
- Kullanıcının istekleri dışında herhangi bir işlem yapma.
- Özel bir işlem gerekiyorsa kullanıcıdan onay iste.

## Sonuç

Bu dosya, proje genelindeki bütün sprintler için güvenli, izlenebilir ve sprint kontrollü çalışmanın temel talimatlarını tanımlar.
