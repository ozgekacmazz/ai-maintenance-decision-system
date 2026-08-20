# Accessibility audit — Sprint 21B

Date: 20 August 2026. Scope: the Sprint 21 browser UI, WCAG 2.2 AA-oriented review in the isolated `sensor_e2e` environment. Automated evidence uses Playwright and `@axe-core/playwright` 4.13.0; keyboard, responsive CSS and semantic markup were also reviewed manually. This is not a formal conformance certification.

## Findings and disposition

| Severity | Area and evidence | Impact | Disposition |
| --- | --- | --- | --- |
| Serious | Decision, priority override and user-management overlays had no dialog semantics, focus trap, Escape handling or focus restoration. | Keyboard and screen-reader users could lose context. | Fixed with the shared `useAccessibleDialog` hook and browser coverage. |
| Serious | Login errors were not associated with their inputs; user-management email/role labels and password help were not programmatically linked. | Errors and field purpose could be missed. | Fixed with ids, `htmlFor`, `aria-describedby`, `aria-invalid`, alerts and correct autocomplete tokens. |
| Serious | Clickable prediction rows had no keyboard equivalent. | Keyboard-only users could not open prediction detail. | Fixed with Enter/Space activation and an accessible link name. Work-order/replay rows retain native detail buttons, avoiding nested interactive roles. |
| Serious | Axe found sidebar teal text at 3.74:1 and muted role text at 4.34:1 in the modal-open state. | Normal text missed the 4.5:1 AA threshold. | Fixed by darkening the shared teal and muted tokens. |
| Moderate | Data tables lacked captions and explicit column scopes. | Table purpose/header navigation was less clear. | Fixed on prediction, work-order, replay, user and confusion-matrix tables. |
| Moderate | No skip link or consistent visible focus ring. | Repeated navigation was costly and focus could be difficult to locate. | Fixed with “İçeriğe geç” and a 3 px `:focus-visible` ring. |
| Minor | Dialogs could exceed a short viewport. | Controls could become unreachable at zoom/small height. | Fixed with bounded height and internal scrolling. |

No blanket axe rule disable, `.skip`, `.fixme` or `.only` is used. Automated routes cover login; USER dashboard, quick analysis, predictions, work orders, replay and unauthorized view; ADMIN machine, stock, user and log management; and open create/reset dialogs. Critical/serious violations are required to be zero. Modal tests cover initial focus, wraparound, Escape and opener restoration. Existing `prefers-reduced-motion` CSS is retained. Tables use horizontal scrolling at narrow widths; dialogs use viewport-bounded scrolling. Manual 320 px/200% review found no loss of controls, but this is not a device-lab certification.

Loading, empty, error and validation components retain visible text/status semantics. Active navigation includes text/context and is not color-only. Priority, risk and status badges contain text. The confusion matrix is a real table with caption and row/column scopes. There is no dark mode to audit.
