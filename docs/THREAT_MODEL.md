# Threat model (v0.2)

## Default posture

- Local-only CLI / optional local API.
- No outbound network requirement for core screening.
- No control-plane / SCADA integration in codebase.
- HTML reports escape dynamic text.
- Upload size and row/column limits enforced.

## Residual risks

- Poisoned or mis-unitized CSV can produce misleading cards (mitigate with schema + quality gates).
- If API is exposed beyond localhost, add authN/Z, TLS, rate limits, dependency pinning review.
- Logs must not dump full production well files by default.

## Explicit non-goals

Remote command execution, actuation, model training on customer data inside this repository demo.
