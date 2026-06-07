# Naming Conventions (Pipelet Suite)

This repo follows the **suite-wide identifier glossary**. New DB columns, API
fields, and route params must use the canonical vocabulary — not deprecated
aliases. A `naming-lint` CI check (`tools/naming_lint.py`,
`.github/workflows/naming-lint.yml`) enforces this on added lines only.

**Canonical names (quick reference):**

| Use | Not |
|---|---|
| `tenant_id` (RLS scope; resolve from operator, never assume `operator_id == tenant_id`) | `provider_id`, `emsp_id`, `operator_id`-as-scope |
| `operator_id` (INT FK → `op_cpms_operators.id`; **1:n** — a tenant owns many operators) | — |
| `cpo_operator_id` / `oicp_operator_id` (the OCPI/OICP CPO string `DE*ABC`) | `operator_id` for the string id |
| `chargepoint_id` (the OCPP-1.6 charge-box identity) | `station_id`, `cp_id`, `ocpp_station_id`, `charger_id`, `wallbox_id` |
| `connector_id` (INT; **≠ `evse_id`** — an EVSE contains connectors) | `connector_idx`, `connectorId` (except on the wire) |
| `evse_ocpi_id` (String `DE*PIP*E0001`) vs `evse_row_id` (INT PK) | bare `evse_id` (overloaded String/INT) |
| `rfid_uid` (`.strip().upper()`) | `id_tag`, `uid`, `single_uuid`, `rfid_uuid` |
| `emaid` (ISO-15118 PnC — never folded into RFID) | — |
| `auth_token` (login/bearer/OCPI cred) | bare `token` as an identity field |
| `session_uid` (internal) · `session_id` (OCPI) · `transaction_id` (OCPP) | mixing these layers |
| `driver_id` (EV driver) · `user_id` (operator/admin staff) | reusing `user_id` for a driver |

**Protocol-defined wire fields are untouchable** (`chargePointId`, `idTag`,
`idToken`, `transactionId`, `connectorId`, `chargeBoxIdentity`,
`chargingStation`, OCPI `uid`/`contract_id`).

Full glossary, rationale, and migration plan:
**Outline → "Naming Conventions & Identifier-Glossar (Suite-weit)"**
(`/doc/naming-conventions-identifier-glossar-suite-weit-uE9crckEJU`) and
`~/dev/pipelet/NAMING.md`.

Suppress a justified lint exception with a trailing `naming-lint: ignore` comment.
