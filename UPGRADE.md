# Upgrading steward-canary

## 1.8.0 → 1.8.1 (data format 2, forward-only)

1.8.1 converts the data volume to format 2 on its first start. The conversion is one-way: 1.8.0 refuses to start on
a format 2 volume ("downgrade not supported"). Before upgrading:

1. Drain the queue: `POST /drain`, then confirm `GET /status` reports `"pending": 0`. Items still pending at
   conversion time are lost (`app/upgrade.py` PRECONDITIONS `queue_drained`).
2. Upgrade only from 1.8.0.
