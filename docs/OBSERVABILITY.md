# İzlenebilirlik ve Güvenli Loglama

`TraceIdMiddleware` her isteğin başında `request.trace_id` oluşturur. İstemcinin
`X-Trace-ID` değeri yalnız `A-Z`, `a-z`, `0-9`, `.`, `_`, `-` karakterleri ve
1–64 uzunluk koşulunda korunur; aksi halde UUID üretilir. Middleware tüm
response'lara `X-Trace-ID` ekler. Hata gövdesi ile header aynı değeri taşır.

Middleware zincirinde trace middleware dış katmandadır; böylece CSRF, Django 404,
DRF ve başarılı yanıtların tümünü görür. Yalnız `/api/` hata gövdelerini JSON
sözleşmesine dönüştürür; admin HTML davranışına dokunmaz.

Her tamamlanan istek standart Python logging ile JSON satırı üretir:

- `event`
- `trace_id`
- `method`
- query string içermeyen `path`
- `status_code`
- `duration_ms`

Request/response body, query string, Authorization, Cookie, Set-Cookie, CSRF,
username, parola, access/refresh token, Django secret ve veritabanı parolası
loglanmaz. Beklenmeyen exception için kullanıcıya yalnız genel 500 yanıtı verilir;
log kaydı trace ID ve exception türüyle sınırlıdır. Development konsolu okunabilir
JSON üretir. Production log taşıma, saklama, erişim politikası ve harici
observability servisi bu sprintin kapsamı dışındadır.

Destek akışında kullanıcıdan hata ekranındaki takip kodu alınır ve aynı
`trace_id` loglarda aranır. Bu kod secret değildir; buna rağmen log injection'a
karşı doğrulanır.
