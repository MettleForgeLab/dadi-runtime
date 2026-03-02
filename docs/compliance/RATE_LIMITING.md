# Distributed Rate Limiting (Redis)

The gateway supports tenant-scoped rate limiting with either:
- in-memory token buckets (single instance)
- Redis-backed token buckets (multi-instance)

## Env

- `DADI_RATE_LIMIT_ENABLED=true|false`
- `DADI_RATE_LIMIT_BACKEND=redis|memory`
- `REDIS_URL=redis://host:6379/0`
- `DADI_RATE_LIMIT_FAIL_CLOSED=true|false`

Lane settings (capacity + refill rate):
- `DADI_RL_*` env vars (see `services/gateway/dadi_gateway/rate_limit.py`)

## Production note

Redis backend should point to a managed Redis/ElastiCache instance.
In production, fail closed if Redis is unavailable.
