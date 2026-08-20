# Performance baseline — Sprint 21B

Date: 20 August 2026. Environment: local Windows host, Docker Desktop, isolated PostgreSQL `sensor_e2e`, development Django server and demo data (10 predictions, 4 work orders, one 250-item replay). These values are diagnostic local baselines, not production SLAs.

## API baseline

Warm authenticated requests were measured with DRF's production views and PostgreSQL query capture. The first prediction request took 2742 ms because model/contract data was cold-loaded; the immediately repeated request took 10.42 ms.

| Endpoint | Queries | Warm ms | Bytes |
| --- | ---: | ---: | ---: |
| Prediction list/dashboard feed | 3 | 10.42 | 5,856 |
| Prediction detail | 8 | 22.05 | 10,763 |
| Work-order list | 3 | 13.89 | 6,907 |
| Work-order detail | 3 | 11.79 | 3,753 |
| Admin prediction logs | 3 | 16.15 | 6,497 |
| Machine list | 2 | 4.83 | 1,888 |
| Stock list | 2 | 6.71 | 2,141 |
| Replay list | 2 | 9.97 | 903 |
| Replay detail/metrics | 3 | 11.86 | 1,203 |
| Replay items | 5 | 16.89 | 10,975 |
| Input-domain contract | 0 | 6.56 | 588 |

Query-budget regressions passed: work-order list/detail ≤5; prediction list ≤6/detail ≤8; admin logs ≤5; replay list/detail/items ≤3/4/5 for base data. A separate relation-rich replay test records 2/4/6, and replay items remain exactly 6 queries for both one and ten successful records. Existing selectors use annotations, `select_related` and bounded prefetches; no N+1 fix or budget increase was needed. Pagination defaults to 20 and rejects values outside 1–100.

## PostgreSQL plans and indexes

`EXPLAIN (ANALYZE, BUFFERS)` on demo data measured machine-filtered prediction ordering at 0.130 ms and priority-filtered work-order ordering at 0.045 ms; PostgreSQL correctly chose sequential scans for the 10- and 4-row tables. Replay `(oturum_id, sira)` used the existing unique index and returned 20 rows in 0.069 ms. Foreign-key and uniqueness indexes already cover replay/session/item joins and core relationships. The small dataset does not demonstrate a defensible plan improvement for indexes on `olcum_zamani`, `olusturulma_zamani`, `genel_oncelik` or `etkin_genel_oncelik`; therefore no speculative migration was added. Re-measure with representative production cardinality/selectivity before adding composite filter/order indexes.

## Frontend and journey

Before route lazy loading, the main JS chunk was 395.57 kB raw / 107.33 kB gzip and CSS was 18.77/4.04 kB. After lazy loading all pages with an accessible Suspense fallback, main JS is 249.37/80.39 kB and CSS 19.19/4.16 kB. The largest route chunk is prediction detail at 25.48/6.25 kB. This reduces initial gzip JS by about 25%; ADMIN/replay code is no longer in the normal USER initial chunk. Production build emits no size warning and source maps remain disabled by the existing Vite policy.

The final two consecutive clean real journeys measured 17.5 s and 15.6 s. The final real 250-item replay measured 46.7 s (earlier runs: 48.4 s and 41.2 s), consistent with the established 41–49 s local range. No P0 issue was observed. P1 cold model initialization is visible only on the first prediction-list access; P2 future work is representative-cardinality index remeasurement. No memoization, virtual-list dependency or arbitrary performance threshold was introduced.
