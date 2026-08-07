# ADR-0005: Distributed Locking as a Separate Responsibility

- **Status:** Accepted
- **Date:** 2026-08-06
- **Decision Makers:** CARE Fork Maintainers
- **Supersedes:** None
- **Superseded by:** None

## Context

CARE currently implements lock-like behavior through cache and Redis-related operations.

Verified patterns include:

- `cache.set(..., nx=True)`;
- backend-specific arguments;
- direct Redis access;
- a LocMem compatibility implementation that accepts `nx` but always succeeds.

This can silently remove mutual exclusion when the cache backend changes.

A lock is not a cache value.

The project must support portable deployment profiles without allowing backend substitution to weaken concurrency correctness.

## Decision

Distributed locking SHALL be treated as an independent infrastructure responsibility.

Lock acquisition and release SHALL not depend on undocumented cache-backend extensions.

CARE SHALL use an explicit locking interface limited to verified application requirements.

The lock implementation SHALL provide clearly defined semantics for:

- acquisition;
- contention;
- timeout;
- expiration or lease behavior;
- release;
- ownership;
- failure;
- process termination;
- duplicate release.

The final initial backend SHALL be selected only after every lock call site is analyzed.

## Backend candidates

Acceptable candidates for evaluation include:

- PostgreSQL advisory locks;
- PostgreSQL row-level locking;
- unique constraints and transactional state transitions;
- Redis locks;
- removal of a lock where a database constraint is the correct mechanism.

Different call sites MAY require different mechanisms.

The project SHALL not force every concurrency problem through one generic distributed-lock service.

## Database correctness first

When the invariant can be enforced using:

- unique constraints;
- conditional updates;
- `SELECT ... FOR UPDATE`;
- transaction isolation;
- idempotency records;

those database mechanisms SHOULD be preferred over a cache lock.

A lock SHALL not replace a durable database invariant.

## PostgreSQL advisory locks

PostgreSQL advisory locks MAY be used when:

- all contenders share PostgreSQL;
- lock scope can be represented safely;
- session or transaction lifetime is understood;
- connection-pool behavior is compatible;
- failure and cleanup semantics are tested.

They SHALL not be adopted automatically for every call site.

## Redis locks

Redis-compatible locks MAY remain an option when:

- low-latency distributed coordination is genuinely required;
- Redis is enabled for the deployment profile;
- lease expiration and ownership are implemented correctly;
- provider command support is verified.

Redis SHALL not be mandatory solely because existing code used `nx`.

## No fake locking

A backend SHALL not claim success without providing actual exclusion.

Unsupported lock behavior SHALL fail explicitly.

LocMem may provide process-local locks only when the documented scope is explicitly process-local. It SHALL not impersonate a distributed lock.

## Observability

Lock contention and timeout SHOULD be observable without logging sensitive records.

Useful metadata includes:

- lock category;
- opaque resource identifier;
- wait duration;
- timeout;
- acquisition result;
- process role.

## Consequences

### Positive

- Cache swaps cannot silently remove locking.
- Concurrency semantics become explicit.
- Database invariants can replace unnecessary locks.
- Redis remains optional where not required.
- Lock behavior becomes testable.

### Negative

- Every lock call site requires analysis.
- More than one coordination mechanism may remain.
- PostgreSQL advisory locks require careful connection handling.
- Redis locks require correct lease and ownership behavior.

## Alternatives Considered

### Keep `cache.set(nx=True)`

Rejected.

It is not part of Django's portable cache contract and already fails silently under the current LocMem shim.

### Use one universal Redis lock

Rejected as the default.

It would make Redis mandatory and could hide database-integrity problems.

### Use one universal PostgreSQL advisory-lock service

Rejected before call-site analysis.

Some invariants are better enforced with constraints or row locks.

### Remove all locks

Rejected.

Some operations may genuinely require mutual exclusion.

## Out of Scope

This ADR does not select the final backend for every lock.

That selection belongs to IS-05 after call-site analysis and concurrency tests.

## Related Documents

- Cache and Redis inventory
- ADR-0004: Configurable Application Cache
- IS-05: Distributed Lock Modernization

## Implementation Status

- [x] Decision accepted.
- [ ] Lock call sites classified.
- [ ] LocMem false-lock behavior removed.
- [ ] Database invariants identified.
- [ ] Approved lock mechanisms implemented.
- [ ] Concurrency tests completed.
