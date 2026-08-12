# Beckn (NFH) integration

Adds `care/beckn`, connecting Care to a Beckn network in both roles: as a **BPP**
(Care provides care to the network) and as a **BAP** (Care requests care from the
network on behalf of the Care frontend).

Everything lives in `care/beckn`; the only changes elsewhere are the `BECKN_*`
settings and the URL includes.

## Care as BPP (inbound)

The ONIX adapter verifies the signature and forwards the action to
`POST /api/v1/beckn/bpp/webhook/<action>` — `discover`, `select`, `init`,
`confirm`, `status`, `update`, `cancel`. The view returns only an ACK/NACK; the
matching `on_*` callback is delivered asynchronously via `BECKN_BPP_CALLER_URL`.

Each payload resolves to one of two flows:

- **appointment** — books a real `TokenSlot` / `TokenBooking` through Care scheduling.
- **referral** — creates or updates a `ResourceRequest`.

Booking changes made later inside Care (cancel, reschedule, fulfil) push an
unsolicited `on_status` back to the BAP. Fulfilling a booking also completes the
referral it came from — the link is written to `booking.meta["beckn"]`
(`coordinationRef`) at confirm time, with Redis kept only as a fast path.

`cancel` and `update` are implemented for the appointment flow only; a BAP that
sends either against a referral gets a NACK.

### Referral guards

The webhook is unauthenticated by design, so the inbound payload has to carry its
own guarantees:

- `init` is idempotent — a retry updates the referral found by coordination id
  instead of creating a second one, and never pulls an approved referral back to
  pending.
- `confirm` must carry an `ACTIVE` contract status, and only a `pending` referral
  is transitioned. A replayed confirm on an approved referral refreshes the
  stored contract; one on a referral that has been cancelled, rejected or
  completed is refused.
- The `bapId` seen when the referral was created is persisted, and an action from
  a different BAP is refused.
- A contract with no PATIENT participant is refused rather than producing a
  referral with no patient.
- The referring contact number is normalised (a `tel:` prefix and separators are
  dropped, a bare Indian mobile gains `+91`) and put through Care's phone
  validator, which does not otherwise run on `save()`. An unusable number is
  stored as empty.

## Care as BAP (outbound)

The frontend drives `discover -> select -> confirm` through
`POST /api/v1/beckn/bap/<action>` and polls
`GET /api/v1/beckn/bap/transaction/<transaction_id>`. Counterparty callbacks
arrive at `/api/v1/beckn/bap/receiver/<action>`.

In-flight state is held in Redis (`services/txn_store.py`), so a `discover` costs
nothing durable — the `ResourceRequest` is created only on `on_confirm`. The
`service_type` selects a flow adapter (`services/flows/`: consultation,
appointment) that owns the payload shapes and the confirm side effect.

`discover` is a broadcast, so several BPPs may answer one transaction. Each
reply's routing is stored under its own `bppId` (`routingByBpp`), and a
`select`/`confirm` must name the chosen provider in `context.bppId` when more than
one answered — otherwise the request is refused with a 400 rather than addressed
to whichever replied last. The choice is remembered for later actions.

`on_confirm` always leaves something durable behind: the consultation flow
creates (or approves) a `ResourceRequest`, and the appointment flow records the
confirmed contract on the referral named by `coordinationRef`, moving it to
`transfer_in_progress`, or on a `ResourceRequest` created for a standalone
booking. Inbound `on_status`/`on_update`/`on_cancel` are applied to that record
too, so a referral the counterparty cancels or completes does not sit at
`approved` forever.

A callback for a transaction Care no longer holds (expired, unknown, or Redis
down) is logged in full at error level and dropped — it cannot be applied to
anything.

See [beckn_fe_plugin.md](beckn_fe_plugin.md) for the frontend contract.

## Catalog

```bash
python manage.py publish_beckn_catalog [--dry-run] [--all] [--coordination]
```

Builds a catalog per facility from its schedulable resources and schedules, then
publishes it through the BPP caller. Per-resource overrides live in
`Schedule.meta["beckn"]`: `healthServiceType`, `acceptanceMode`, `bppId`/`bppUri`.

## Care coordinator (manual review)

A resource whose schedule sets `acceptanceMode: MANUAL_REVIEW` does not
auto-confirm. `confirm` creates a `pending` booking and reports a DRAFT contract;
once a coordinator books it in Care, an `on_status` with ACTIVE follows.
`--coordination` publishes the desk itself as a `ServiceCoordinationResource`.

## Patients

An inbound patient is resolved in this order, and only created when none of these
match:

1. the ABHA number carried in `participantAttributes.healthIds`
   (`services/identifiers.py`, stored as a `PatientIdentifier`);
2. the patient already on the referral the payload names (`coordinationRef` for a
   booking, `coordinationId` for a referral being amended);
3. name and date of birth, confined to the origin facility's geo organization.

Outbound `confirm` payloads describe the patient with name, gender, date of birth
and the ABHA, so the counterparty can match a person it already knows. The Care
patient id is deliberately not sent — it means nothing off this instance. In a
loopback deployment the frontend's chosen patient wins: `on_confirm` repoints the
referral at it if the local BPP resolved a different one.

## Settings

Read from the environment; the identity and URL settings default to empty.

| Purpose | Settings |
| --- | --- |
| BPP identity and delivery | `BECKN_BPP_ID`, `BECKN_BPP_URI`, `BECKN_BPP_CALLER_URL` |
| BAP identity and delivery | `BECKN_BAP_ID`, `BECKN_BAP_URI`, `BECKN_BAP_CALLER_URL` |
| Coordination centre (default BPP for outbound) | `BECKN_CC_BPP_ID`, `BECKN_CC_BPP_URI` |
| Network | `BECKN_NETWORK_ID`, `BECKN_VERSION`, `BECKN_SYSTEM_USERNAME` |
| Coordinator catalog | `BECKN_COORDINATOR_*` |

With no caller URL configured, outbound delivery is skipped and Care behaves as
if the integration were absent.

### Callback routing

`BECKN_BAP_URI` is the address counterparties send `on_*` callbacks to, and it
should be the receiver path:

```
BECKN_BAP_URI=https://<host>/api/v1/beckn/bap/receiver
```

A callback that lands on the plain action path (`/bap/on_confirm`) or on the BPP
webhook is still applied to its transaction rather than dropped, which keeps a
loopback deployment working when both roles share one url — but the exchange is
easier to follow when the advertised uri is right.

### One identity per deployment

`BECKN_BPP_ID`, `BECKN_BAP_ID` and `BECKN_SYSTEM_USERNAME` all default to
instance-agnostic values, and nothing stops two deployments claiming the same
network id. Two Care instances talking to each other (one as BAP, one as BPP)
must each be given their own:

| Setting | Why it must differ |
| --- | --- |
| `BECKN_BPP_ID` / `BECKN_BPP_URI` | a shared id makes provider replies ambiguous, and the per-BPP routing above collapses back to one entry |
| `BECKN_BAP_ID` / `BECKN_BAP_URI` | callbacks are routed by these; sharing them sends one instance's callbacks to the other |
| `BECKN_SYSTEM_USERNAME` | the audit user for records the integration creates; keep it distinct so the two instances' records are attributable |

Patient identity across two Care databases rests on the ABHA number: it is the
only key both sides share, so an ABHA-less referral cannot be correlated beyond
name and date of birth.

## Layout

```
api/         webhook (BPP) · bap_webhook (BAP callbacks) · bap_actions (frontend)
builders/    on_* callback and outbound payload construction · participants
services/    handlers · receiver (inbound on_*) · flows/ · catalog · scheduling ·
             patient · txn_store
mappers.py   read values out of inbound Beckn payloads
signals.py   booking changes -> unsolicited on_status
```
