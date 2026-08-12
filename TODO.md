# Beckn referral remediation plan

Issues found while reviewing the inbound (BPP) referral path and the
Care-as-BAP orchestration. Each item notes the class of failure it removes and
the deployment topologies that need it.

## Context for a fresh developer

Everything here lives in `care/beckn`. Read [docs/beckn.md](docs/beckn.md)
first for the module overview, and
[docs/beckn_fe_plugin.md](docs/beckn_fe_plugin.md) for the frontend contract.

### Vocabulary

- **BAP** — the buyer-side app; it *asks* for care. **BPP** — the provider-side
  app; it *offers* care. Care plays both roles, in separate code paths.
- **Actions and callbacks** — a BAP sends `discover`, `select`, `init`,
  `confirm`, `status`, `update` or `cancel`; the BPP replies asynchronously with
  the matching `on_*`. The synchronous HTTP response is only ever an ACK/NACK.
- **ONIX** — the network adapter sitting between Care and the network. It
  verifies signatures inbound, and signs and routes outbound. Care posts its
  outbound actions to `BECKN_BAP_CALLER_URL` and its outbound callbacks to
  `BECKN_BPP_CALLER_URL`; when neither is set, delivery is skipped and Care
  behaves as if the integration were absent.
- **NFH schema** — the health vocabulary layered on Beckn core: a contract is a
  `HealthReferral` or a `HealthContract`, catalogs carry `HealthResource` and
  `HealthOffer`. `contractAttributes.@type` is what tells them apart.
- **T1 / T2** — T1 is the referral itself; T2 is the downstream booking made
  against it, which points back via `coordinationRef`.
- **transactionId vs coordinationId** — `transactionId` identifies one Beckn
  exchange (and is the Redis key). `coordinationId` identifies the referral
  across exchanges, and is what correlates a `confirm` to an existing
  `ResourceRequest`.

### Two flows, one set of endpoints

`select`/`init`/`confirm`/`status`/`cancel` are shared, and
`mappers.resolve_flow` routes each payload to one of:

- **referral** — creates and approves a `ResourceRequest` (`services/handlers.py`,
  `builders/referral.py`);
- **appointment** — drives Care scheduling, `TokenSlot` and `TokenBooking`
  (`services/scheduling.py`, `builders/catalog.py`).

### Where state lives

- `ResourceRequest.extensions["beckn"]` — coordination id, transaction id and
  the contract snapshot. This is the durable record.
- `TokenBooking.meta["beckn"]` — transaction id, bap id, and the inbound
  context/message for later unsolicited `on_status` callbacks.
- Redis, via `services/txn_store.py` — in-flight BAP exchanges under
  `beckn:txn:*` (24h TTL) and the booking-to-referral link under
  `beckn:booking-referral:*` (90d). Note `IGNORE_EXCEPTIONS: True` on the cache:
  a Redis failure returns `None` rather than raising, which several items below
  are about.

### Running things

There is no host venv, `pipenv` or `ruff` on this machine — use the containers:

```bash
make test path="care.beckn"                          # or care.emr
docker compose exec backend ruff check care/beckn
docker compose exec backend ruff format care/beckn
```

### Current state

Branch `ccn_merge_v0.1`. Every item below is either done or recorded as a
deliberate decision not to do it (items 12 and 20). `make test path="care.beckn"`
runs 31 tests, all passing, including the two that had never passed.

## Topologies

| Tag | Meaning |
| --- | --- |
| `self` | One Care instance is both BAP and BPP (loopback) |
| `care-care` | Care instance A (BAP) talking to Care instance B (BPP) |
| `care-ext` | Care as BAP against a third-party BPP |
| `ext-care` | Third-party BAP against Care as BPP |

`care-care` is `care-ext` on the sending instance plus `ext-care` on the
receiving one — there is no third code path. What it adds is patient identity
across two databases, where ABHA is the only shared key.

All four topologies are covered by the items below. What is *not* covered is a
live network: nothing here has been exercised against a real ONIX pair, so the
next step is an end-to-end run of each topology.

## Phase 1 — Unblock the referral flow

Nothing else matters until these land: an inbound referral is created but can
never be approved, and in a loopback deployment it is never created at all.

- [x] **1. Correlate referrals by coordination id.** `self` `care-care` `ext-care`
      *Fixes: functional breakage (every `confirm` NACKs).*
      `find_resource_request` matched only on `contract.id`, which the referral
      builder never set, so `_referral_confirm` and `_referral_status` always
      raised "Referral not found". Falls back to the stored `coordinationId`,
      which both sides already agree on.

- [x] **2. Set `contract["id"]` on referral callbacks.** `self` `care-care` `ext-care`
      *Fixes: functional breakage; protocol inconsistency.*
      `_inject_referral` now assigns the referral's `external_id` to the
      contract id, as the appointment flow already does.

- [x] **3. Create the referral on `confirm` when `init` was skipped.** `self` `care-care` `ext-care`
      *Fixes: functional breakage in loopback and for BAPs that omit init.*
      `_referral_init` was the only creation point, but the BAP adapter only
      emits discover/select/confirm. `_referral_confirm` now creates the
      referral directly as `approved` when the lookup misses.

## Phase 2 — Stop losing data silently

- [x] **4. Make the booking-to-referral link durable.** `self` `care-care` `ext-care`
      *Fixes: silent, permanent data loss.*
      `coordinationRef` is now written to `booking.meta["beckn"]` at confirm and
      read before Redis, which stays as a fast path. Only an explicit
      `coordinationRef`/`coordinationId` counts (`mappers.get_coordination_ref`),
      so an appointment booked outside a referral is no longer linked to one by
      the old contract-id/transaction-id fallbacks. A fulfilled Beckn booking
      with no link, or one whose referral cannot be found, is logged.
      `test_fulfilled_booking_completes_referral` passes.

- [x] **5. Stop treating an unknown transaction as success.** `self` `care-care` `care-ext`
      *Fixes: silent loss of in-flight exchanges.*
      The callback is logged in full at error level (payload included, so the
      exchange can be reconstructed) and dropped; the endpoint still ACKs, as the
      protocol requires. **Decision:** no store for orphan callbacks — persisting
      them to Redis would not survive the Redis outage that is one of the causes,
      and a table was not worth it.

## Phase 3 — Idempotency and state correctness

- [x] **6. Make `init` idempotent.** `ext-care`
      *Fixes: duplicate records under normal network retries.*
      `_referral_init` looks the referral up first and refreshes it (fields,
      assigned facility, contract snapshot) instead of creating a second one. The
      status is left alone, so an init that arrives after the confirm cannot pull
      an approved referral back to pending.

- [x] **7a. Send patient identity on outbound confirms.** `self` `care-care` `care-ext`
      *Fixes: duplicate/incorrect patient records at the BPP.*
      Both outbound flows now build the PATIENT participant through
      `builders.outbound.build_patient_participant`: when the frontend names a
      Care `patient`, its name, gender, date of birth and ABHA are carried.
      **Decision:** the Care patient `external_id` is *not* sent — it is
      meaningless off the instance. Loopback is covered instead by 7b's matching
      and by `on_confirmed` repointing the referral at the patient the frontend
      selected.

- [x] **7b. Deduplicate patients without an ABHA at the BPP.** `self` `care-care` `ext-care`
      *Fixes: duplicate clinical records.*
      `find_or_create_patient` now resolves ABHA, then the patient on the
      referral the payload names (`coordinationRef`/`coordinationId`), then name
      and date of birth within the origin facility's geo organization, before
      creating anything.

- [x] **8. Guard the confirm transition.** `ext-care`
      *Fixes: state corruption on replay.*
      A non-`ACTIVE` inbound contract status is refused, and only a `pending`
      referral is transitioned. A confirm replayed on an approved referral
      refreshes the snapshot; one on a cancelled/rejected/in-transfer/completed
      referral is refused.

- [x] **9. Reject referrals with no patient.** `self` `care-care` `ext-care`
      *Fixes: silently incomplete clinical records.*
      `_create_referral` raises `BecknActionError` when the contract carries no
      PATIENT participant.

## Phase 4 — Security and data quality

- [x] **10. Bind the confirm to the initiating BAP.** `ext-care` `care-care`
      *Fixes: unauthorized state change.*
      The `bapId` is persisted in `extensions["beckn"]` when the referral is
      created and checked on every later `init`/`confirm` (`_assert_same_bap`); a
      mismatch NACKs. A payload with no `bapId` cannot be checked, so it is
      allowed through rather than breaking counterparties that omit it.

- [x] **11. Validate the referring contact number.** `ext-care`
      *Fixes: invalid data bypassing model validators.*
      `_clean_contact_number` strips a `tel:` prefix and separators, adds `+91` to
      a bare Indian number, and runs Care's own validator; anything that still
      fails is stored as empty.

- [ ] **12. Derive `category` from the payload.** `ext-care`
      **Decision: not doing this.** A referral is `patient_care`; the payload has
      no field that reliably says otherwise, so it stays hardcoded.

- [x] **13. Pin down loopback callback routing.** `self`
      *Fixes: silent ACK-and-drop, plus spurious 403s.*
      **Decision: forward rather than reject.** A regex route ahead of the
      catch-all sends `bap/on_*` to the (unauthenticated) BAP receiver, and an
      `on_*` arriving at the BPP webhook is applied to its transaction instead of
      being ACKed into the void. The handling moved to
      `services/receiver.py`, which all three paths share. `BECKN_BAP_URI` is
      documented in `docs/beckn.md`.

## Phase 5 — Cleanup

- [x] **14. Remove the dead branch in `_resolve_flow_by_lookup`.**
      *Fixes: pointless query.* The `ResourceRequest` lookup is gone and the
      unused `context` argument with it.

- [x] **15. Fix `test_create_and_advance_status`.**
      *Fixes: a test that has never passed.* It now asserts the `actions` list
      and fetches each payload with `get_action`. The `cache.clear()` calls in
      these tests were also removed: the cache is one shared Redis database, so
      clearing it wiped the transactions of the other `--parallel` processes.

- [x] **16. Correct the stale docstrings.**
      *Fixes: documentation that actively misleads.* The `txn_store` record shape
      is now the real one (`context`/`actions`/`error`, plus `routingByBpp` from
      item 17). `signals.py` already described the meta-based booking link, which
      item 4 made true.

## Phase 6 — Multi-instance topologies

Gaps in the Care-as-BAP direction, which the phases above did not cover.

- [x] **17. Store routing per BPP instead of last-writer-wins.** `care-ext` `care-care`
      *Fixes: select/confirm addressed to the wrong provider.*
      `set_routing` keeps each reply under its own `bppId` in `routingByBpp`
      (`routing` still holds the last reply, which is what a single-BPP exchange
      uses). `select`/`confirm` resolve the routing through
      `txn_store.resolve_routing` and are refused with a 400 when several BPPs
      answered and none was named in `context.bppId`.

- [x] **18. Persist a confirmed remote appointment.** `care-ext` `care-care`
      *Fixes: silent data loss after 24 hours.*
      `AppointmentFlow.on_confirmed` records the confirmed contract on the
      referral named by `coordinationRef` (moving it to `transfer_in_progress`, so
      the network sees `BOOKING_CONFIRMED`), or on a `ResourceRequest` created for
      a standalone booking. Either way the id is linked to the transaction as
      `resourceRequestId`. A confirm that names neither a referral nor a facility
      is logged at error level, since nothing can be persisted for it.

- [x] **19. Apply inbound lifecycle callbacks to the referral.** `care-ext` `care-care`
      *Fixes: local state diverging from the counterparty.*
      `on_status`/`on_update`/`on_cancel` now run `FlowAdapter.on_lifecycle`,
      which maps the callback's contract status and `lifecycleState` onto the Care
      referral status. A `DRAFT` state is ignored (it would undo an approval), and
      a completed referral is never changed, so replays are no-ops.

- [ ] **20. Support `cancel`/`update` for the referral flow.** `ext-care` `care-care`
      **Decision: not doing this.** The hole stands; it is now documented in
      `docs/beckn.md` and the frontend contract, so a BAP knows to expect a NACK.

- [x] **21. Document distinct network identities per instance.** `care-care`
      *Fixes: ambiguous callback routing.*
      `docs/beckn.md` now has "One identity per deployment" — why each of
      `BECKN_BPP_ID`/`BECKN_BAP_ID`/`BECKN_SYSTEM_USERNAME` must differ, plus the
      note that ABHA is the only patient key two instances share.
