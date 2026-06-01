# JissouParkEmpire Audit Report - Turn 44

## 1. Audit Target
- **Target Module:** `app/routes/game_routes.py`, `app/game_engine.py`
- **Target Routes/Functions:** `/build` (`action_build`), `/train` (`action_train`), `/birth` (`action_birth`)
- **Audit Focus:** Completeness of the AP Blackhole (`[LOGIC-F016]`) fix, Resource Validation

## 2. Methodology
- **Audit Type:** Source code review, Logic flow analysis.
- **Reference Standard:** `AI_AUDIT_DOC_STANDARD.md`
- **Execution:**
  1. Reviewed the `v1.7.0` changes applied to mitigate the AP Blackhole issue (`[LOGIC-F016]`).
  2. Cross-referenced the pre-checks added in `game_routes.py` with the remaining validation logic inside `game_engine.py` actions.
  3. Identified edge cases where validation failures still result in un-refunded AP consumption.

## 3. Findings

### 3.1. [LOGIC-F017] Incomplete Fix for AP Blackhole (Resource Pre-checks Missing)
- **Severity:** High (Usability / Logic Flaw)
- **Vulnerability Type:** Logic Error, Resource Loss
- **Description:**
  While `v1.7.0` successfully moved `consume_turn` below several basic validations (e.g., target validation, unit count checks) in `game_routes.py`, it completely missed **resource requirement checks**.
  For example, in the `/build` route:
  ```python
      # game_routes.py
      if building_type not in GC.BUILDINGS: ... # OK
      turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=1) # AP Deducted & Committed
      success, result, messages = game_engine.action_build(park, building_type)
  ```
  Inside `action_build()` (`game_engine.py`):
  ```python
      updated = Park.query.filter(
          Park.id == park.id,
          Park.material >= bldg['material_cost']
      ).update(...)
      if updated == 0:
          return False, {}, [f"자재가 부족한 데스! ..."]
  ```
  If the player lacks sufficient `material`, `action_build` returns `False`, but the AP was already deducted by `consume_turn` in the route. The route flashes the error message and redirects, meaning the AP is permanently lost with no refund.

  This identical pattern persists in:
  - **`/train` & `action_train`**: Fails on `total_np_available < GC.TRAIN_NP_COST` after AP is consumed.
  - **`/birth` & `action_birth`**: Fails on `total_np_available < GC.BIRTH_NP_COST` after AP is consumed.
- **Impact:**
  - Players will still permanently lose AP if they attempt to build, train, or give birth without sufficient resources (NP or material).
  - Continues to severely degrade user experience and game balance by punishing invalid inputs with irreversible time-resource (AP) loss.
- **Remediation Recommendation:**
  1. **Option A (Route-level Pre-checks):** Add resource checks directly in `game_routes.py` before calling `consume_turn`.
     - Build: `if park.material < GC.BUILDINGS[building_type]['material_cost']: return error`
     - Train: `if park.total_np_available < GC.TRAIN_NP_COST: return error`
     - Birth: `if park.total_np_available < GC.BIRTH_NP_COST: return error`
  2. **Option B (Engine-level Refund):** If `action_*` functions return `False` due to resource shortage, the route should refund the AP (`park.action_points += ap_cost; db.session.commit()`).

## 4. Remediation

### 4.1. [LOGIC-F017] Fix Details
- **Modified Files:** `app/routes/game_routes.py`
- **Change Summary:**
  - Applied **Option A (Route-level Pre-checks)** as recommended.
  - Added deterministic resource validation checks directly in `game_routes.py` *before* calling `consume_turn()` for all three affected routes:
    - `/build`: `if park.material < GC.BUILDINGS[building_type]['material_cost']: return error`
    - `/train`: `if park.total_np_available < GC.TRAIN_NP_COST: return error`
    - `/birth`: `if park.total_np_available < GC.BIRTH_NP_COST: return error`
  - If any pre-check fails, the route flashes an appropriate error message and returns immediately without consuming AP.
  - The engine functions (`action_build`, `action_train`, `action_birth`) retain their atomic resource checks as the final source of truth for race-condition safety.

## 5. Conclusion
The incomplete AP Blackhole fix (`[LOGIC-F017]`) has been resolved. All resource-consuming actions (`/build`, `/train`, `/birth`) now validate required materials and NP *before* AP deduction. Players will no longer lose AP due to insufficient resources for these actions.
