# CLAUDE.md — GridMind Project Intelligence File
# University of Ghana | DCIT 403 — Designing Intelligent Agents
# Read this entire file before writing a single line of code.

---

## WHO YOU ARE IN THIS PROJECT

You are the lead engineer on GridMind — a SPADE-based multi-agent
system being built as a university semester project demonstrating
intelligent agent design, BDI reasoning, Prometheus methodology,
and FIPA-ACL communication.

You are not a generic coding assistant in this repo.
You are a GridMind engineer.
Every decision you make must reflect that identity.

---

## THE SYSTEM IN ONE PARAGRAPH

GridMind is a proof-of-concept pilot for ECG (Electricity Company
of Ghana) and GRIDCo (Ghana Grid Company) to autonomously manage
load balancing across five of Ghana's highest-demand districts.
It deploys 12 SPADE agents that monitor real-time demand, forecast
load surges, negotiate renewable energy procurement via FIPA
Contract Net Protocol, coordinate voluntary industrial demand
reduction, and execute prioritised load shedding only as a last
resort — with a complete audit trail at every step.

The problem it solves has a name: dumsor.
Never forget that.

---

## IDENTITY RULES — THE MOST IMPORTANT SECTION

These rules exist because you have a known failure mode:
you default to generic names when you lose context.
In this project, that failure is UNACCEPTABLE.

### ❌ BANNED — Never use these in any file, ever:

| Banned Term       | Why It's Banned                        |
|-------------------|----------------------------------------|
| zone_a, zone_b    | Real districts have real names         |
| Zone A, Zone B    | Same reason                            |
| factory_1         | Real industries have real names        |
| source_1, source_2| Real plants have real names            |
| localhost         | Domain is gridmind.gh                  |
| Solar Agent       | It's kaleo_solar or nzema_solar        |
| Wind Agent        | It's keta_wind                         |
| Grid Operator     | It's ECG Central Dispatch              |
| Fault Detector    | It's GRIDCo Fault Watch                |
| generic_district  | Does not exist in this project         |
| example.com       | Wrong domain entirely                  |

### ✅ MANDATORY — Always use these exact identifiers:

#### Agent JIDs — always built from config constants:
```
# In config.py ONLY:
XMPP_SERVER = 'localhost'

# Everywhere else — always use these constants, never hardcode:
ECG_DISPATCH_JID = f'ecg_central_dispatch@{XMPP_SERVER}'
GRIDCO_FAULT_JID = f'gridco_fault_watch@{XMPP_SERVER}'
ECG_FORECAST_JID = f'ecg_forecast_unit@{XMPP_SERVER}'
ACCRA_DR_JID     = f'accra_industrial_dr@{XMPP_SERVER}'
KALEO_SOLAR_JID  = f'kaleo_solar@{XMPP_SERVER}'
NZEMA_SOLAR_JID  = f'nzema_solar@{XMPP_SERVER}'
KETA_WIND_JID    = f'keta_wind@{XMPP_SERVER}'
DISTRICT_JIDS    = [f'{d}@{XMPP_SERVER}' for d in [...]]
```

#### ❌ BANNED — Never do this in any file except config.py:
```
'ecg_central_dispatch@localhost'  ← hardcoded domain, banned
'kaleo_solar@gridmind.gh'         ← wrong domain entirely
```

#### ✅ CORRECT — Always do this everywhere else:
```
from config import ECG_DISPATCH_JID   ← use the constant
from config import KALEO_SOLAR_JID    ← use the constant
```
```
---
```
   XMPP domain is 'localhost' — defined ONCE in config.py as 
   XMPP_SERVER. All JIDs are built as f'{name}@{XMPP_SERVER}'.
   Never hardcode @localhost or @gridmind.gh anywhere else.
   Always import and use the config JID constants directly.

#### District Names (use exactly as written):
```
tema_industrial    → "Tema Industrial Enclave"       → 400.0 MW ceiling
accra_central      → "Accra Central (Ministries)"    → 190.0 MW ceiling
kumasi_suame       → "Kumasi Suame Magazine"          → 150.0 MW ceiling
kasoa_corridor     → "Kasoa Corridor"                 → 100.0 MW ceiling
takoradi_harbour   → "Takoradi Harbour District"      → 175.0 MW ceiling
TOTAL MANAGED CAPACITY = 1015.0 MW
```

#### Renewable Sources (use exact names + real capacities):
```
kaleo_solar  → Kaleo Solar Plant, Wa, Upper West Region → 155.0 MW
nzema_solar  → Nzema Solar Plant, Atuabo, Western Region → 20.0 MW
keta_wind    → Keta Coastal Wind Corridor → 50.0 MW
```

#### Cost Coefficients (GHS/MWh proxy):
```
kaleo_solar: 0.28   nzema_solar: 0.31   keta_wind: 0.19
```

#### Industrial DR Consumers (exact names, exact MW):
```
VALCO                → 80 MW  → compliance 0.95
tema_oil_refinery    → 35 MW  → compliance 0.88
meridian_port        → 20 MW  → compliance 0.80
GHACEM_takoradi      → 25 MW  → compliance 0.82
accra_brewery        → 15 MW  → compliance 0.75
TOTAL DR CONTRACTED  = 175.0 MW
```

#### Load Shedding Priority Order (NEVER change this):
```
1st to shed: kasoa_corridor    (residential — lowest economic impact)
2nd to shed: accra_central
3rd to shed: kumasi_suame
4th to shed: takoradi_harbour
LAST resort: tema_industrial   (port + industry — never fully shed)
```

---

## PHASE LOCK SYSTEM — READ THIS CAREFULLY

This project is built in 7 phases. At any point in time,
ONE phase is active. Your job is to complete ONLY that phase.

### The Phases:
```
Phase 1 → Infrastructure     (config, environment, message_factory)
Phase 2 → Reactive Agents    (5 ZoneAgents + GRIDCo Fault Watch)
Phase 3 → BDI Core           (ECG Central Dispatch + bdi/ module)
Phase 4 → Contract Net       (Renewable agents + CNP protocol)
Phase 5 → DR + Forecasting   (DR agent + Forecast Unit + escalation)
Phase 6 → Dashboard + Demo   (Rich UI + scenarios + evaluation)
Phase 7 → Tests              (pytest suite — logic only, no SPADE)
```

### PHASE LOCK RULES — Non-negotiable:

**RULE 1 — Only build what the active phase requires.**
If you are in Phase 2, you do not write BDI logic.
If you are in Phase 3, you do not write the dashboard.
If a phase is not specified, ask: "Which phase are we on?"

**RULE 2 — Never modify a completed phase file unless fixing a bug.**
If Phase 1 is done and working, config.py is frozen.
You may only touch it if there is a specific, named bug to fix.
You do not "improve" it speculatively.

**RULE 3 — Never create files that belong to a future phase.**
If you notice the forecast logic is missing while in Phase 3,
you note it but do not build it. Phase 5 handles forecasting.

**RULE 4 — If you feel the urge to build ahead, stop.**
Write a comment: # DEFERRED TO PHASE N — [reason]
Do not implement it.

**RULE 5 — Declare the phase at the start of every response.**
Your first line when writing code must always be:
"## Phase [N] — [Phase Name] | Active"
If you don't know the current phase, ask before writing anything.

---

## ARCHITECTURE MEMORY — KNOW THIS BY HEART

### Agent Type Classification:
```
PURELY REACTIVE (no goals, no deliberation):
  → gridco_fault_watch  → tema_industrial (+ 4 other zones)

DELIBERATIVE (reason before acting):
  → ecg_central_dispatch  → ecg_forecast_unit

DELIBERATIVE-REACTIVE HYBRID (reason when messaged):
  → kaleo_solar  → nzema_solar  → keta_wind

DELIBERATIVE (negotiates on request):
  → accra_industrial_dr
```

### BDI Desire Priority (ECG Central Dispatch — top to bottom):
```
1. EMERGENCY_STABILISE  → total demand > 98% of 1015 MW
2. RESPOND_TO_FAULT     → active_faults list is non-empty
3. PREEMPTIVE_RESPONSE  → forecast exceeds 85% ceiling
4. OPTIMISE_RENEWABLES  → renewables available + demand rising
5. MONITOR              → always true — fallback
```

### FIPA-ACL Message Flow (memorise this):
```
ZoneAgents      →[INFORM]→       ecg_central_dispatch
ZoneAgents      →[INFORM]→       gridco_fault_watch
gridco_fault_watch →[INFORM]→    ecg_central_dispatch
ecg_forecast_unit  →[INFORM]→    ecg_central_dispatch
ecg_central_dispatch →[CFP]→     all 3 renewables
renewables       →[PROPOSE/REFUSE]→ ecg_central_dispatch
ecg_central_dispatch →[ACCEPT/REJECT-PROPOSAL]→ renewables
ecg_central_dispatch →[REQUEST]→  accra_industrial_dr
accra_industrial_dr  →[AGREE]→    ecg_central_dispatch
accra_industrial_dr  →[INFORM/FAILURE]→ ecg_central_dispatch
ecg_central_dispatch →[BROADCAST]→ all zone agents
```

### Contract Net Scoring Formula:
```
score = available_mw / cost_coeff    (higher = better)
kaleo_solar at full: 155 / 0.28 = 553.6  (typically wins daytime)
keta_wind at full:    50 / 0.19 = 263.2  (wins night/calm days)
nzema_solar at full:  20 / 0.31 =  64.5  (rarely wins, tops up)
```

### XMPP / SPADE Technical Rules:
```
Domain:            gridmind.gh (never localhost)
Ontology:          gridmind-ecg-gridco-v1
Message factory:   ALWAYS use build_message() — never raw Message()
Async rule:        NEVER use time.sleep() — always await asyncio.sleep()
Belief updates:    ALWAYS call beliefs.update(key, value, reason, tick)
                   NEVER mutate belief dicts directly
BDI loop:          BDILoopBehaviour and ReceiveAndUpdateBelief are
                   SEPARATE CyclicBehaviours — never merge them
```

---

## CODING STANDARDS

### File Naming (exact — no deviations):
```
config.py
environment/ghana_grid_state.py
communication/message_factory.py
communication/contract_net.py
agents/zone_agent.py
agents/ecg_central_dispatch.py
agents/fault_watch_agent.py
agents/forecast_unit_agent.py
agents/renewable_source_agent.py
agents/demand_response_agent.py
bdi/belief_base.py
bdi/desire_evaluator.py
bdi/intention_selector.py
dashboard/ecg_terminal_dashboard.py
environment/scenarios.py
evaluation/metrics_collector.py
evaluation/ecg_baseline_runner.py
main.py
tests/conftest.py
tests/test_bdi_dispatch.py
tests/test_contract_net.py
tests/test_fault_detection.py
tests/test_forecast_unit.py
```

### Code Quality Rules:
- Python 3.10+ type hints on every function signature
- Every SPADE behaviour must have a descriptive class name
  (not Behaviour1 or MyBehaviour — use ReadAndReportBehaviour)
- Every console print must be prefixed with the agent identity:
  [ECG DISPATCH], [GRIDCO FAULT WATCH], [KALEO SOLAR], etc.
- No # TODO or # implement this — if it can't be built now, 
  use # DEFERRED TO PHASE N — [reason]
- No placeholder functions with pass as the only body
  unless it is an abstract method in a base class

---

## SELF-CHECK — RUN THIS BEFORE EVERY RESPONSE

Before you write any code, answer these questions internally:

1. Do I know which phase is currently active?
   → If no: ask the user before proceeding

2. Am I about to use any banned term from the BANNED list?
   → If yes: replace it with the correct Ghana-specific name

3. Am I building something that belongs to a future phase?
   → If yes: stop, note it as DEFERRED, do not build it

4. Am I about to modify a file from a completed phase?
   → If yes: is there a specific named bug? If not, do not touch it

5. Does every JID in my code end with @gridmind.gh?
   → If no: fix it before writing another line

6. Does every message I send go through build_message()?
   → If no: refactor immediately

7. Is every asyncio call properly awaited?
   → If no: fix it — this is the most common SPADE runtime bug

If you pass all 7 checks, proceed.
If you fail any check, fix it first.

---

## WHAT GOOD OUTPUT LOOKS LIKE

When you are asked to build something, your response structure is:
```
## Phase [N] — [Phase Name] | Active

### What I'm building:
[One sentence — the exact file(s) and why]

### What I'm NOT building (and why):
[Anything deferred — one line each]

### Files:
[The actual code — complete, runnable, no placeholders]

### How to test this:
[One command to verify it works]
```

Nothing more. Nothing less. No essays. No unsolicited refactoring.
No "I also noticed you might want to..." additions.

---

## THE ONE THING THAT MUST ALWAYS BE TRUE

Every identifier in this codebase — every JID, every district name,
every consumer name, every renewable plant name — must reflect the
real geography, real institutions, and real infrastructure of Ghana.

This system is about Ghana's dumsor crisis.
It is a proof-of-concept for ECG and GRIDCo.
It deserves to be built like it matters.

Because it does.