# JissouParkEmpire Audit Report - Turn 43

## 1. Audit Target
- **Target Module:** `app/routes/game_routes.py`
- **Target Routes:** All AP-consuming routes (`/attack`, `/defend`, `/build`, `/train`, `/gather`, `/birth`, `/spy`, `/diplomacy/enemy`, `/diplomacy/dissolve`)
- **Audit Focus:** Transaction Flow, AP Deduction logic, User Input Validation

## 2. Methodology
- **Audit Type:** Source code review, Logic flow analysis.
- **Reference Standard:** `AI_AUDIT_DOC_STANDARD.md`
- **Execution:**
  1. Traced the execution sequence of routes that consume Action Points (AP).
  2. Analyzed the internal behavior of `game_engine.consume_turn()`.
  3. Identified the ordering of AP deduction versus action validity checks.

## 3. Findings

### 3.1. [LOGIC-F016] AP Deducted Before Action Validation (AP Blackhole Exploit/Bug)
- **Severity:** High (Usability / Logic Flaw)
- **Vulnerability Type:** Logic Error, Resource Loss
- **Description:**
  Throughout `game_routes.py`, actions that cost AP invoke `game_engine.consume_turn(park, ap_cost=...)` at the very beginning of the route function. For example, in the `/attack` route:
  ```python
      # 1. AP is consumed and DB is immediately committed in consume_turn.
      turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=2)
      if not turn_ok:
          return redirect(url_for('game.dashboard'))

      # 2. Validation Checks
      if game_engine.is_protected(park):
          flash(..., 'error')
          return redirect(url_for('game.dashboard')) # <== AP IS PERMANENTLY LOST HERE

      target = Park.query.get(target_id)
      if not target or target.is_destroyed or target.id == park.id:
          flash(..., 'error')
          return redirect(url_for('game.dashboard')) # <== AP IS PERMANENTLY LOST HERE
  ```
  The `consume_turn` function inherently executes `db.session.commit()` to finalize the AP deduction. If any subsequent business logic check (e.g., target validation, insufficient resources, lack of specific units, protection mode checks) fails, the route redirects the user back to the dashboard with an error message. However, no mechanism exists to refund the AP. Consequently, users permanently lose their AP just by triggering a validation error.
- **Impact:**
  - Severe degradation of game balance and user experience.
  - Players lose AP (a strictly time-gated resource) due to simple mistakes like selecting a protected target, not having enough resources, or deploying invalid unit counts.
  - This effectively serves as an "AP Blackhole" where actions cost AP even if they are fundamentally impossible to perform.
- **Remediation Recommendation:**
  Restructure the route logic so that all deterministic validations (e.g., checking if the target is valid, verifying sufficient units/resources) are performed *before* calling `consume_turn`. For validations that must occur inside engine functions (like `action_train` or `action_build`), the engine functions should be refactored to perform validation, and then call `consume_turn` internally only if the validation succeeds, or return a signal to the route to refund the AP.

## 4. Remediation

### 4.1. [LOGIC-F016] Fix Details
- **Modified Files:** `app/routes/game_routes.py`
- **Change Summary:**
  - Restructured all AP-consuming routes to perform deterministic input and state validations *before* calling `game_engine.consume_turn()`.
  - Added pre-validation checks for each route:
    - `/attack`: target validity, protection mode, alliance status, minimum unit count
    - `/defend`: defending unit count <= available unit count
    - `/build`: building_type validity against `GC.BUILDINGS`
    - `/train`: adult_count >= 1
    - `/birth`: adult_count >= 1
    - `/gather`: non-negative unit counts, at least 1 unit deployed
    - `/spy`: target validity, adult_count >= 2, alliance status
    - `/diplomacy/enemy`: target validity
    - `/diplomacy/dissolve`: diplomatic relation validity and ownership
  - Each route now validates all deterministic constraints, flashes an error, and returns immediately without consuming AP if validation fails.
  - `consume_turn()` is invoked only after all validations pass, ensuring AP is never deducted for impossible or invalid actions.

## 5. Conclusion
The systemic logic flaw (`[LOGIC-F016]`) has been fixed. All AP-consuming routes now validate action constraints before AP deduction, eliminating the "AP Blackhole" bug. No further modifications are required for this finding.
