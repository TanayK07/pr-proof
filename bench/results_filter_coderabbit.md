PRs with verdicts: 49
Real bugs kept:  72/77 (93.5%)
Noise removed:   76/223 (34.1%)

| | Precision | Recall | F1 | Issues posted |
|---|---|---|---|---|
| coderabbit | 25.7% | 56.2% | 35.2% | 300 |
| coderabbit + pr-proof filter | 32.9% | 52.6% | 40.4% | 219 |

Real bugs the filter dropped:
  keycloak_keycloak-36880: Feature flag guard at line 77 only checks ADMIN_FINE_GRAINED_AUTHZ (V1), but when only ADMIN_FINE_GRAINED_AUTHZ_V2 is enabled, the entire cl
  ai-code-review-evaluation_sentry-greptile-3: Truthiness check 'if client_sample_rate:' may skip valid sample_rate of 0 or 0.0, should use explicit None check 'if client_sample_rate is n
  grafana_grafana-79265: updateDevice returning ErrDeviceLimitReached when rowsAffected == 0 is semantically incorrect - zero rows affected could mean the device doe
  grafana_grafana-79265: Potential time skew in limit check - CountDevices uses time.Now().UTC() while subsequent upsert operations use device.UpdatedAt, which may d
  calcom_cal.com-10967: The createEvent method signature in LarkCalendarService is missing the credentialId parameter required by the Calendar interface, violating 
