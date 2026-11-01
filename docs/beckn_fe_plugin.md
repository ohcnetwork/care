# Care FE plugin — Beckn NFH (referral + appointment)

A complete spec/prompt for building a Care frontend plugin that drives the
Beckn NFH flows against the Care backend.

## 1. What the backend does (context)

Care BE is a Beckn participant that acts as **both** a BAP (for the Care FE) and
a BPP (for external apps) via two ONIX adapters. **The FE only talks to the BAP
side.** The FE never builds/sends Beckn to the network directly — it calls Care
BE REST endpoints; Care BE wraps the payload in a Beckn `context`, sends it
through ONIX, and records every request + `on_*` callback in **Redis** under one
`transactionId`. The FE drives the flow and **polls one endpoint** for progress.

Two flows, same endpoints, chosen by `service_type`:

- `consultation` → a referral; on confirm the BE creates a `ResourceRequest`.
- `appointment` → a booking; the BE (as BPP) returns catalog → slots → books a
  `TokenBooking`.

All actions are asynchronous: an action call returns immediately (`202` +
`transactionId`); the real result arrives later as an `on_*` callback that the FE
sees by polling.

## 2. Auth

All BAP endpoints require JWT: header `Authorization: Bearer <access>`. Get it
from `POST /api/v1/auth/login/ {username,password}` → `{access, refresh}`.

## 3. Endpoints (base `/api/v1/beckn`)

- **`POST /bap/<action>`** — initiate an action. `<action>` ∈
  `discover, select, init, confirm, status, cancel, update`.
  - `discover` starts a new transaction (needs `service_type`); returns
    `{ transactionId, result }`.
  - all others need `transactionId` in the body.
  - Body fields: `service_type` (discover only), `transactionId`, `message` (raw
    Beckn message — passthrough), `context` (overrides like `bppId`/`bppUri`/
    `networkId`/`schemaContext`), and `query` (used only if you omit `message`
    for discover).
  - `result` ∈ `ack | nack | error | skipped`.
- **`GET /bap/transaction/<transactionId>`** — the poll endpoint.
  - No param → lightweight status record (fast to poll): `status`, `routing`,
    `context`, `actions` (keys recorded so far), `resourceRequestId`.
  - `?action=<action>` (e.g. `on_discover`) → just that action's stored
    `{context, message}` payload: `{ transactionId, status, action, ready, data }`.
- Referral status (Phase-2 completion) is read from the normal resource API:
  **`GET /api/v1/resource/<resourceRequestId>/`** → `status` becomes `completed`
  when the appointment is fulfilled.

## 4. The transaction record

Each action's request/response payload is stored under its **own** Redis key
(`beckn:txn:<id>:<ACTION>`); the transaction id holds only a small status
record. Poll the small record, then fetch a single slice when you need it.

**Status record — `GET /bap/transaction/<id>`:**
```json
{
  "transactionId": "…",
  "serviceType": "consultation | appointment",
  "status": "DISCOVER|ON_DISCOVER|SELECT|ON_SELECT|CONFIRM|ON_CONFIRM|INIT|ON_INIT|STATUS|ON_STATUS|CANCEL|ON_CANCEL|UPDATE|ON_UPDATE|NACK|ERROR",
  "routing":  { "bppId": "…", "bppUri": "…", "bapId": "…", "bapUri": "…" },
  "context":  { "networkId": "…", "bppId": "…", "bppUri": "…" },
  "actions":  ["DISCOVER", "ON_DISCOVER", "SELECT", "ON_SELECT", "CONFIRM", "ON_CONFIRM"],
  "resourceRequestId": "…"
}
```

**Action slice — `GET /bap/transaction/<id>?action=on_discover`:**
```json
{ "transactionId": "…", "status": "ON_DISCOVER", "action": "ON_DISCOVER",
  "ready": true, "data": { "context": {}, "message": { "catalogs": [] } } }
```
`ready:false` / `data:null` means that action hasn't arrived yet.

**Polling rule:** poll the status record every ~1–2s. Keep polling while `status`
is a request state (`DISCOVER/SELECT/CONFIRM/…`); when it flips to the matching
`ON_*`, fetch that slice with `?action=on_<action>`; stop on `NACK`/`ERROR`.

## 5. Data shapes the FE renders

Fetch each with `GET /bap/transaction/<id>?action=<action>` → read `data.message`.

- **Catalog** (`?action=on_discover` → `data.message.catalogs[]`): each has
  `descriptor.name`, `provider{id,descriptor.name}`, routing
  `bppId/bppUri/bapId/bapUri`, `resources[]` (practitioner / healthcare_service /
  location with `resourceAttributes.availabilitySchedule[]`), and `offers[]`
  (`id`, `descriptor.name`). → render a provider/offer dropdown; keep the chosen
  `offer.id`, `resource.id`, and the catalog's `bppId/bppUri`.
- **Slots** (`?action=on_select` → `data.message.contract.performance[]`): each has `id`
  (slotId) + `performanceAttributes.appointmentWindowStart/End`,
  `healthServiceType`. → render selectable time slots.
- **Confirmation** (`?action=on_confirm`): show success; for consultation, read
  `resourceRequestId` from the status record.

## 6. Curls — Consultation (referral) flow

```bash
BASE=http://localhost:8000            # match runserver port
TOKEN=…                               # from /api/v1/auth/login/

# 1) discover (JSONPath search supported)
curl -X POST $BASE/api/v1/beckn/bap/discover -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "service_type":"consultation",
  "context":{"schemaContext":["https://schema.beckn.io/HealthResource/v2.1/context.jsonld"]},
  "message":{"intent":{"textSearch":"cardiology",
    "filters":{"type":"jsonpath","expression":"$.catalogs[*].resources[*] ? (@.resourceAttributes.healthServiceType == \"PHYSICAL_CONSULTATION\")"}}}
}'                                      # -> {"transactionId":"TID","result":"ack"}

# 2) poll the status record until status = ON_DISCOVER
curl $BASE/api/v1/beckn/bap/transaction/TID -H "Authorization: Bearer $TOKEN"
# then fetch just the catalog slice
curl "$BASE/api/v1/beckn/bap/transaction/TID?action=on_discover" -H "Authorization: Bearer $TOKEN"

# 3) select chosen offer + provider routing (bppId/bppUri from the catalog)
curl -X POST $BASE/api/v1/beckn/bap/select -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "transactionId":"TID",
  "context":{"bppId":"cnn_beck_bpp.ohc.network","bppUri":"http://onix-bpp:8082/bpp/receiver"},
  "message":{"contract":{"status":{"code":"DRAFT"},
    "commitments":[{"id":"c1","offer":{"id":"offer-coord-specialist"},"resources":[{"id":"res-…","quantity":{"count":1}}]}],
    "contractAttributes":{"@type":"hrf:HealthReferral","coordinationId":"TID"}}}
}'                                      # poll -> ON_SELECT

# 4) confirm (facility from contractAttributes.facilityId or top-level "facility")
curl -X POST $BASE/api/v1/beckn/bap/confirm -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "transactionId":"TID",
  "message":{"contract":{"status":{"code":"ACTIVE"},
    "participants":[{"descriptor":{"name":"Meena Joshi"},"participantAttributes":{"@type":"hpa:HealthParticipant","participantRole":"PATIENT","healthIds":[{"system":"ABHA","value":"91-…"}]}}],
    "contractAttributes":{"@type":"hrf:HealthReferral","coordinationId":"TID","facilityId":"<FACILITY_UUID>","lifecycleState":"ACTIVE"}}}
}'                                      # poll -> ON_CONFIRM, read resourceRequestId
```

Context (`bppId/bppUri/networkId`) sent once is remembered in Redis and
auto-applied to later actions.

## 7. Curls — Appointment flow (same endpoints, `service_type=appointment`)

```bash
# discover
curl -X POST $BASE/api/v1/beckn/bap/discover -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "service_type":"appointment",
  "message":{"intent":{"filters":{"type":"jsonpath","expression":"$.catalogs[*].resources[*] ? (@.resourceAttributes.healthServiceType == \"PHYSICAL_CONSULTATION\")"}}}
}'                                      # poll -> ON_DISCOVER (providers + practitioners/services + availability)

# select a resource -> get slots
curl -X POST $BASE/api/v1/beckn/bap/select -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "transactionId":"TID",
  "context":{"bppId":"cnn_beck_bpp.ohc.network","bppUri":"http://onix-bpp:8082/bpp/receiver"},
  "message":{"contract":{"status":{"code":"DRAFT"},
    "commitments":[{"id":"c1","resources":[{"id":"<RESOURCE_ID>","quantity":{"count":1}}],"offer":{"id":"offer-<RESOURCE_ID>"}}],
    "contractAttributes":{"@type":"hct:HealthContract","healthServiceType":"PHYSICAL_CONSULTATION"}}}
}'                                      # poll -> ON_SELECT (message.contract.performance[] = slots)

# confirm the chosen slot (+ coordinationRef to link the originating referral)
curl -X POST $BASE/api/v1/beckn/bap/confirm -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "transactionId":"TID",
  "message":{"contract":{"status":{"code":"ACTIVE"},
    "commitments":[{"id":"c1","resources":[{"id":"<RESOURCE_ID>","quantity":{"count":1}}],"offer":{"id":"offer-<RESOURCE_ID>"}}],
    "participants":[{"descriptor":{"name":"Meena Joshi"},"participantAttributes":{"participantRole":"PATIENT","healthIds":[{"system":"ABHA","value":"91-…"}]}}],
    "performance":[{"id":"<SLOT_ID>","performanceAttributes":{"healthServiceType":"PHYSICAL_CONSULTATION","appointmentWindowStart":"2026-07-09T04:54:00+00:00","appointmentWindowEnd":"2026-07-09T05:18:00+00:00"}}],
    "contractAttributes":{"@type":"hct:HealthContract","healthServiceType":"PHYSICAL_CONSULTATION","coordinationRef":"<referral coordinationId>"}}}
}'                                      # poll -> ON_CONFIRM (booking created)
```

## 8. Referral → completed

When the appointment's `TokenBooking` is later set to `fulfilled` (normal Care
appointment completion), the linked `ResourceRequest` becomes `completed`. FE
reflects this by `GET /api/v1/resource/<resourceRequestId>/` →
`status == "completed"`.

## 9. FE plugin responsibilities

1. **Auth**: obtain/refresh JWT; attach to every call.
2. **Discover screen**: form for `service_type` + a text search + optional
   JSONPath filter (or simple `query`); call `POST /bap/discover`; store
   `transactionId`.
3. **Poller**: generic hook that polls `GET /bap/transaction/<id>` (status
   record) and, when `status` flips to an `ON_*`, fetches that slice via
   `?action=on_<action>`; stop on `ON_*` / `NACK` / `ERROR`.
4. **Catalog view**: render the `on_discover` slice `data.message.catalogs[]` →
   provider/offer dropdown; capture chosen `offer.id`, `resource.id`, and
   provider `bppId/bppUri`.
5. **Select → slots**: call `POST /bap/select` with chosen offer + routing; poll →
   render `ON_SELECT` slots (appointment) or coordinator confirmation
   (consultation).
6. **Confirm**: call `POST /bap/confirm` with patient
   (`participants`/`healthIds`) + slot (appointment) or `facilityId`
   (consultation) + `coordinationRef` when appointment references a referral;
   poll → `ON_CONFIRM`; show success + `resourceRequestId`.
7. **Status views**: optionally call `POST /bap/status` (passthrough
   `message.contract.id`) and read `ON_STATUS`.
8. **Referral tracking**: show the `ResourceRequest` status
   (`approved` → `completed`).
9. **Error UX**: `result:"skipped"` = network not configured;
   `status:"NACK"/"ERROR"` = show failure with `responses`/error detail.

## 10. Rules & gotchas

- Always poll after every action; the action response only returns
  `{transactionId, result}`.
- Send provider routing (`context.bppId/bppUri`) once (at `select`); it's
  remembered for later actions.
- `init/status/cancel/update` are **passthrough-only** — you must send `message`.
- Redis TTLs: transaction 24h; appointment→referral link 90d.
- Use the same `transactionId` for the whole discover→…→confirm exchange.

## 11. Build-ready: state machine & suggested structure

**Per-transaction state machine (FE):**
```
idle
 └─(POST discover)→ DISCOVER ──poll──▶ ON_DISCOVER  → show catalog
                                  └─▶ NACK|ERROR      → show error
 ON_DISCOVER ─(POST select)→ SELECT ──poll──▶ ON_SELECT → show slots/coordinator
 ON_SELECT   ─(POST confirm)→ CONFIRM ──poll──▶ ON_CONFIRM → success (+ resourceRequestId)
```
Same machine for `appointment` (ON_SELECT carries slots) and `consultation`
(ON_CONFIRM sets `resourceRequestId`). Optional `status/cancel/update` follow the
same request→`ON_*` pattern.

**Suggested plugin structure:**
- `api/beckn.ts` — thin client: `login()`, `action(name, body)` → `POST /bap/<name>`,
  `getStatus(tid)`, `getSlice(tid, action)`.
- `hooks/useBecknTransaction.ts` — starts a transaction, polls `getStatus` on an
  interval, auto-fetches the `ON_*` slice, exposes `{status, slice, error}`,
  stops on `ON_CONFIRM`/`NACK`/`ERROR`.
- `components/DiscoverForm` — `service_type` + text search + optional JSONPath.
- `components/CatalogPicker` — provider/offer dropdown from the catalog slice;
  captures `offer.id`, `resource.id`, provider `bppId/bppUri`.
- `components/SlotPicker` (appointment) — renders `performance[]` slots.
- `components/ConfirmPanel` — collects patient (`participants`/`healthIds`) +
  `facilityId`/slot + optional `coordinationRef`; calls confirm.
- `components/ReferralStatus` — polls `GET /api/v1/resource/<id>/` for
  `approved → completed`.

**Minimal client contract (TypeScript-ish):**
```ts
type ActionResult = { transactionId: string; result: "ack"|"nack"|"error"|"skipped" };
type Status = { transactionId: string; serviceType: string; status: string;
                routing: object; context: object; actions: string[]; resourceRequestId?: string };
type Slice  = { transactionId: string; status: string; action: string; ready: boolean; data: any };

action(name, body): Promise<ActionResult>          // POST /bap/<name>
getStatus(tid): Promise<Status>                    // GET  /bap/transaction/<tid>
getSlice(tid, action): Promise<Slice>              // GET  /bap/transaction/<tid>?action=<action>
```
