# JissouParkEmpire Audit Report - Turn 46

## 1. Audit Target
- **Target Module:** `app/routes/game_routes.py`
- **Target Routes:** `/spy/<target_id>`, `/diplomacy/enemy/<target_id>`, `/diplomacy/dissolve/<diplo_id>`, `/diplomacy/accept/<diplo_id>`, `/diplomacy/reject/<diplo_id>`
- **Audit Focus:** Concurrency, Transaction Management, AP Blackhole (Incomplete fixes from previous turns)

## 2. Methodology
- **Audit Type:** Logic Flow Analysis & Concurrency Review
- **Reference Standard:** `AI_AUDIT_DOC_STANDARD.md`
- **Execution:**
  1. Traced the execution flow of `spy_send`, `diplomacy_enemy`, and `diplomacy_dissolve` focusing on `consume_turn()` execution timing relative to subsequent database transactions.
  2. Analyzed `diplomacy_accept` and `diplomacy_reject` for missing atomic state transitions.

## 3. Findings

### 3.1. [LOGIC-F018] Incomplete Fix for AP Blackhole (Diplomacy & Spy Routes)
- **Severity:** High (Player Resource/AP Permanent Loss)
- **Vulnerability Type:** Transaction Isolation Failure, Unhandled Pre-commit
- **Description:**
  In `spy_send`, `diplomacy_enemy`, and `diplomacy_dissolve`, the route calls `game_engine.consume_turn()` before fully validating and securing the resources or state for the action.
  Crucially, `consume_turn()` executes `db.session.commit()` internally to finalize the AP deduction and turn increment.
  - **In `/spy/<target_id>`:** `consume_turn()` is called, then `action_spy()` is invoked. `action_spy()` performs an atomic `UPDATE` to deduct 1 adult. If this `UPDATE` returns 0 (e.g., due to a concurrent combat or trade deducting the adult first), `action_spy()` returns `False`. The route continues and flashes an error, but the AP deducted by `consume_turn()` is **never refunded**, permanently lost.
  - **In `/diplomacy/enemy/<target_id>`:** `consume_turn()` is called, then a `try...except` block attempts to insert the new `Diplomacy` record and `commit()`. If `commit()` throws an `IntegrityError` (due to a concurrent request establishing the same relation), the `except` block catches it and calls `db.session.rollback()`. However, because `consume_turn()` already committed its own transaction earlier, the rollback does **not** restore the AP. The AP is lost.
  - **In `/diplomacy/dissolve/<diplo_id>`:** Similar to enemy declaration, AP is consumed before the diplomatic relation is atomically dissolved, allowing concurrent duplicate requests to consume multiple APs for a single dissolution.
- **Impact:** Players can permanently lose AP without any game benefit when race conditions occur or when validations fail post-`consume_turn()`.
- **Remediation Recommendation:**
  To completely fix AP Blackholes across all routes, AP consumption must be synchronized with the actual action's transaction, or resources/states must be atomically locked *before* `consume_turn()` is executed. Alternatively, `consume_turn()` should not automatically `commit()`, allowing the route to commit or rollback the entire atomic operation (AP + Action) simultaneously.

### 3.2. [STATE-F019] TOCTOU Race Condition in Diplomacy Accept/Reject (Duplicate Event Logs)
- **Severity:** Low (State Inconsistency / Log Spam)
- **Vulnerability Type:** Race Condition (TOCTOU)
- **Description:**
  In both `diplomacy_accept` and `diplomacy_reject`, the state change is not atomic.
  ```python
      diplo = Diplomacy.query.get(diplo_id)
      if not diplo or diplo.status != 'pending':
          ...
      diplo.status = 'active' # or 'rejected'
      add_event(...)
      db.session.commit()
  ```
  If two requests to accept/reject the same diplomacy offer arrive simultaneously, both will bypass the `diplo.status != 'pending'` check, both will change the memory state to `'active'`/`'rejected'`, and both will execute `add_event()`. Because `add_event()` inserts new rows into the `EventLog` table, this results in duplicate event logs being created for a single diplomacy resolution.
- **Impact:** Minor. Event log spam and slightly inconsistent memory state processing.
- **Remediation Recommendation:**
  Use atomic `UPDATE ... WHERE status='pending'` to transition the diplomacy state. If the `UPDATE` returns 0, abort the operation. Proceed to `add_event()` only if the atomic update succeeds.

## 4. Remediation

### 4.1. [LOGIC-F018] Fix Details
- **Modified Files:** `app/routes/game_routes.py`
- **Change Summary:**
  - **`/spy/<target_id>`:** After `action_spy()` returns `False`, an atomic `UPDATE` refunds the AP cost (`GC.SPY_AP_COST`) back to the park's `action_points` before flashing the error. This covers the race condition where the atomic adult deduction in `action_spy()` returns 0.
  - **`/diplomacy/enemy/<target_id>`:** The `except` block now catches `IntegrityError` specifically (instead of bare `Exception`), refunds 1 AP via atomic `UPDATE`, and then flashes the duplicate relation warning.
  - **`/diplomacy/dissolve/<diplo_id>`:** Replaced the in-memory `diplo.status = 'dissolved'` assignment with an atomic `UPDATE ... WHERE status='active'`. If the update returns 0 (another request already dissolved it), 1 AP is refunded before returning an error.

### 4.2. [STATE-F019] Fix Details
- **Modified Files:** `app/routes/game_routes.py`
- **Change Summary:**
  - **`/diplomacy/accept/<diplo_id>`:** Replaced in-memory state assignment with an atomic `UPDATE ... WHERE status='pending'`. The `add_event()` calls are now only executed if the atomic update returns 1, preventing duplicate event logs under concurrent accept requests.
  - **`/diplomacy/reject/<diplo_id>`:** Same pattern—atomic `UPDATE ... WHERE status='pending'` ensures only the first concurrent request transitions the state, and duplicate event logs are eliminated.

## 5. Conclusion
The AP Blackhole vulnerabilities (`[LOGIC-F018]`) in spy and diplomacy routes have been resolved by adding explicit AP refunds when atomic action operations fail after `consume_turn()` has already committed. The TOCTOU race condition in diplomacy accept/reject (`[STATE-F019]`) has been eliminated by using atomic `UPDATE ... WHERE status='pending'` state transitions.
