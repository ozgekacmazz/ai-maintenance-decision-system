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
# Sprint 21C final production verification — 20 August 2026

- Two clean multi-stage production builds completed successfully.
- Exact `sensor21prodsmoke` zero-DB startup completed through DB health → one-shot migration → Gunicorn readiness → Nginx proxy readiness.
- Runtime: backend UID/GID `10001:10001`, proxy `nginx`; both read-only, `cap_drop: ALL`, `no-new-privileges`, explicit tmpfs and no backend/DB host port.
- Images: backend 241,795,759 bytes; proxy 26,082,253 bytes. Runtime has no pytest, Ruff, compiler or source maps. Ephemeral pip-audit found no known third-party runtime vulnerability; the local ML package is not on PyPI.
- SPA CSP and Permissions-Policy enforced without unsafe-inline/eval; static immutable cache, HTML no-cache and API no-store verified. Docs default 404. Login edge limit returned JSON 429 and `Retry-After: 60`. With the trusted upstream HTTPS marker enabled, readiness returned 200 and HSTS returned exactly `max-age=31536000` without the domain-dependent subdomain/preload opt-ins.
- Migration rerun reported no changes. Backend restart preserved `10` predictions, `4` work orders, `1` replay session and `250` replay items. Graceful stop produced exit code 0 for DB/backend/proxy.
- Custom-format backup restored into an isolated empty DB with counts `10/4/1/250/5`; the restore DB and temporary dump were removed.
- Clean working-tree snapshot excluded `.git`, caches, env files and the ambiguous test `__init__.py` change; its separate build and zero-DB smoke passed, then only exact snapshot resources were removed.
- Production-smoke Playwright: headers/CSP/ADMIN/USER/rate-limit 2/2; two consecutive real journeys 16.7 s and 16.6 s; real replay 66 s and 53.1 s. Human narration was not performed; the documented 8–12 minute timed plan combines these click paths with allocated narration.
- Regression: backend 534/534; ML 83/83; frontend 99/99 plus lint/build; contract 4/4; axe 4/4; production smoke 2/2.
- Deploy check warnings are intentionally limited to HSTS include-subdomains and preload opt-ins because the real TLS/domain topology is not supplied. No check is silenced.
- The remaining delivery gate is a real remote clone after Sprint 21 commit/push; it cannot validate the current uncommitted working tree.
