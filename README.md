# steward-canary-src

The "upstream" of the image steward's selftest canary (`ai13f/k8s-image-steward`, `steward selftest`). Each tag is
built by `.github/workflows/build.yml` into the public image `ghcr.io/ai13f/steward-canary:<tag>` with the label
`org.opencontainers.image.revision=<commit>`. Nothing here is secret.

Every case has its own minor line: `vX.Y.0` is the baseline (the main-branch code) and `vX.Y.1` is the case's
release, a single commit on top of it. The selftest policy uses `max_step: patch`, so a baseline of `vX.Y.0` only
ever sees `vX.Y.1` as its target.

| tags | case | change in `vX.Y.1` | truth |
|---|---|---|---|
| v1.1.0 → v1.1.1 | G1 normal bump / K1 apply error | log line only | good (K1's failure is in the gitops baseline) |
| v1.2.0 → v1.2.1 | G2 slow start | image default `READY_DELAY_S=210` | good |
| v1.3.0 → v1.3.1 | K2 crash loop | a background task kills the process 45 s after start | bad |
| v1.4.0 → v1.4.1 | K4 one-way migration | `SCHEMA_VERSION = 2`, `app/migrations/0002_add_owner.sql` | bad without a snapshot |
| v1.5.0 → v1.5.1 | G3 upstream fixes the patched bug | `status.uptime_s()` returns seconds | good; the overlay patch becomes redundant |
| v1.6.0 → v1.6.1 | K3 broken patch | `status.snapshot()` takes one state dict; the overlay no longer fits | bad with the overlay |

The bug the steward's overlay patch fixes: up to the `.0` tags, `status.uptime_s()` reports milliseconds as seconds.
