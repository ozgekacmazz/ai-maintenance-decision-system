# Final doğrulama kaydı

Bu kayıt **19 Ağustos 2026** tarihinde Sprint 20R-E3 teslimi için alınmıştır. Test sayıları yalnız son doğrulama anını ifade eder; kalıcı ürün metriği değildir.

## Ortam

- Backend container: Python 3.12.14, Django 5.2.17, pytest 8.4.2, pytest-django 4.14.0
- ML host: Python 3.12.6, pytest 8.3.2
- Frontend host: Node 22.12.0, npm 11.0.0; desteklenen minimum Node 22.13+
- Frontend: Vite 8.2.1, Vitest 4.1.10
- Docker Engine 29.5.2, Docker Compose 5.1.4, PostgreSQL 17

## Sonuçlar

| Kontrol | Son doğrulama sonucu |
|---|---|
| Backend pytest | 527/527 geçti |
| Frontend Vitest | 99/99 geçti |
| ML pytest | 83/83 geçti |
| Frontend production build | Başarılı |
| ESLint | Başarılı |
| Ruff check | Başarılı |
| Ruff format check | Başarılı |
| Python compileall | Başarılı |
| Django system check | 0 sorun |
| makemigrations check | Değişiklik yok |
| Sıfır DB migration | Başarılı |
| npm audit | 0 vulnerability |

Backend ve seed doğrulaması production/dev veritabanından ayrı geçici PostgreSQL veritabanlarında yapıldı; yalnız açık test hedefleri kullanıldı ve geçici veritabanları kaldırıldı. Demo seed art arda çalıştırıldığında sayılar sabit kaldı ve environment parola değişimi hash üzerinden doğrulandı.

## Bilinen uyarılar

- Backend testlerinde Joblib/NumPy kaynaklı 8.024 `DeprecationWarning` vardır; test sonucunu etkilemez.
- Yerel Node 22.12.0, bir transit paketin istediği 22.13 minimumunun altındadır ve `npm ci` engine uyarısı üretmiştir. Kurulum/test/lint/build başarılıdır; dokümante edilen minimum 22.13+'tır.
- Git line-ending ayarı bazı dosyalar için ileride LF→CRLF dönüşüm uyarısı üretmektedir; `git diff --check` temizdir.

Son doğrulama anında açık başarısız veya atlanmış test borcu yoktur. Sprint 21 uygulanmamıştır ve bu kaydın kapsamında değildir.
