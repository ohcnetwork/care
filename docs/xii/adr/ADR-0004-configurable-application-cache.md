# ADR-0004: Configurable Application Cache

- **Status:** Accepted
- **Date:** 2026-08-06
- **Decision Makers:** CARE Fork Maintainers
- **Supersedes:** None
- **Superseded by:** None

## Context

CARE currently configures Redis as its default Django cache.

Repository inspection identified multiple operations that appear related to Redis but do not all represent ordinary cache behavior:

- standard cache reads and writes;
- report-progress values;
- rate-limit counters;
- `cache.set(..., nx=True)` used as lock-like behavior;
- `cache.delete_pattern(...)`;
- direct `get_redis_connection()` access;
- Celery broker and result storage;
- health checks.

A backend swap from Redis to PostgreSQL or LocMem cannot safely replace all these responsibilities.

The existing LocMem shim accepts an `nx` argument while always returning success, silently removing mutual exclusion. This demonstrates that cache configuration and distributed locking must be separated.

The project wants Redis to be optional, while supporting:

- PostgreSQL-backed shared cache;
- LocMem for process-local performance values;
- Redis-compatible shared cache where beneficial;
- the existing local Redis profile.

## Decision

CARE SHALL use Django's cache framework as the abstraction for disposable cached values.

Cache backend selection SHALL be configuration-driven.

Initial supported cache profiles SHALL include:

```text
postgres
redis
locmem
dummy
```

The default local upstream-compatible profile MAY continue using Redis.

The initial low-service-count cloud profile MAY use Django's PostgreSQL database cache.

Cache SHALL NOT be used as a generic substitute for:

- distributed locks;
- durable application state;
- task queues;
- correctness-critical coordination;
- arbitrary Redis commands.

## Cache semantics

Values stored through the cache API SHALL be disposable.

Deleting or losing all cache entries SHALL not destroy durable CARE state.

Correctness-critical or auditable state SHALL use explicit PostgreSQL models or constraints.

## PostgreSQL cache

PostgreSQL cache SHALL use Django's supported database-cache backend.

It is appropriate for:

- moderate shared cache traffic;
- cross-instance disposable values;
- regenerated configuration;
- selected progress values where expiration is acceptable;
- avoiding a separate Redis service in smaller deployments.

It is not assumed to match Redis latency or throughput.

The cache table SHALL be initialized explicitly during environment setup.

## Redis cache

Redis-compatible storage MAY be used for:

- higher-frequency shared cache;
- lower-latency counters;
- deployments that already operate Redis;
- workloads where PostgreSQL cache pressure becomes excessive.

Configuration SHALL remain provider-neutral.

Upstash or another compatible service may be selected through standard Redis URLs.

## LocMem

LocMem MAY be used only for values that do not require cross-process or cross-instance consistency.

It is appropriate for:

- process-local performance optimization;
- regenerated schema data;
- test or development scenarios.

It SHALL NOT be used for:

- distributed locking;
- globally enforced rate limits;
- shared task progress;
- correctness-sensitive state.

## Report progress

Report progress SHALL be classified separately.

It may use:

- the configured shared cache when disposable progress is sufficient;
- an explicit PostgreSQL model when durability, auditability or failure history is required.

Progress values SHALL not be described or implemented as locks.

## Nonportable cache operations

Operations such as:

```text
delete_pattern
get_redis_connection
backend-specific command execution
```

SHALL not appear in provider-neutral cache consumers.

Each existing use SHALL be:

- eliminated;
- replaced with explicit key tracking;
- moved to a responsibility-specific implementation;
- retained only inside a Redis-specific optional component.

## Failure behavior

Every cache use SHALL define whether cache failure:

- becomes a cache miss;
- produces a controlled degraded response;
- blocks the operation.

Performance caches may fail open as misses.

Correctness-sensitive behavior must not rely on ignored cache exceptions.

## Consequences

### Positive

- Redis becomes optional for ordinary caching.
- PostgreSQL can provide moderate shared cache without another service.
- Cache consumers align with Django.
- Provider-specific Redis operations are isolated.
- Locks and durable state are no longer confused with caching.

### Negative

- PostgreSQL cache adds database queries and table growth.
- Different profiles have different latency characteristics.
- Existing backend-specific cache operations require refactoring.
- Some values may need dedicated models instead of cache.

## Alternatives Considered

### Replace Redis globally with DatabaseCache

Rejected.

Redis currently performs responsibilities beyond caching.

### Keep Redis mandatory

Rejected.

Smaller cloud-native deployments should not require it for ordinary caching.

### Use LocMem as the default cloud cache

Rejected for shared values.

Cloud Run instances do not share LocMem state.

### Create a custom generic cache API

Rejected.

Django already provides the required abstraction for cache semantics.

## Out of Scope

This ADR does not define:

- distributed locks;
- Celery broker selection;
- task queues;
- detailed rate-limit implementation;
- exact report-progress model;
- database sizing;
- Upstash-specific features.

## Related Documents

- Cache and Redis inventory
- ADR-0003: Configurable Asynchronous Execution
- ADR-0005: Distributed Locking
- IS-04: Cache Modernization

## Implementation Status

- [x] Decision accepted.
- [ ] Cache responsibilities classified.
- [ ] PostgreSQL cache implemented.
- [ ] Redis cache retained as optional.
- [ ] LocMem use restricted.
- [ ] Backend-specific operations removed from generic consumers.
- [ ] Report progress assigned to an appropriate backend.
