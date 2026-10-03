PRs with verdicts: 49
Real bugs kept:  67/73 (91.8%)
Noise removed:   46/185 (24.9%)

| | Precision | Recall | F1 | Issues posted |
|---|---|---|---|---|
| copilot | 28.3% | 53.3% | 37.0% | 258 |
| copilot + pr-proof filter | 32.5% | 48.9% | 39.1% | 206 |

Real bugs the filter dropped:
  keycloak_keycloak-36880: registerListener is gated by ADMIN_FINE_GRAINED_AUTHZ (v1) but calls management(...) which can return V2 implementations when ADMIN_FINE_GRA
  ai-code-review-evaluation_sentry-greptile-3: Using Python's built-in `hash()` function can produce different values across process restarts, causing cache inconsistency in distributed s
  grafana_grafana-79265: updateDevice function returns ErrDeviceLimitReached when rowsAffected == 0, but this could happen for multiple reasons (device doesn't exist
  ai-code-review-evaluation_discourse-graphite-9: ensure_loaded! method reads and potentially modifies @loaded_locales without proper synchronization, bypassing LOAD_MUTEX protection used in
  ai-code-review-evaluation_discourse-graphite-4: The `postMessage` target origin is set to the full referrer URL (`request.referer`), but browsers compare the origin (scheme/host/port) only
  calcom_cal.com-10967: The createEvent method signature is missing the credentialId: number parameter that's now required by the Calendar interface
