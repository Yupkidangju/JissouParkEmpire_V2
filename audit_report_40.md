# JissouParkEmpire Audit Report - Turn 40

## 1. Audit Target
- **Target Module:** `app/routes/game_routes.py`
- **Target Functions:** `defend()`
- **Audit Focus:** Concurrency and State Consistency (Phantom Defense Exploit)

## 2. Methodology
- **Audit Type:** Source code review, Data flow analysis, Concurrency analysis.
- **Reference Standard:** `AI_AUDIT_DOC_STANDARD.md`
- **Execution:**
  1. Traced the execution of the `defend()` route.
  2. Analyzed the lock acquisition, release, and session commit cycles.
  3. Identified race windows between `game_engine.consume_turn()` and `db.session.commit()`.

## 3. Findings

### 3.1. [STATE-F013] TOCTOU Race Condition in `/defend` Route (Phantom Defense Exploit)
- **Severity:** High
- **Vulnerability Type:** Concurrency Issue (Time-of-Check to Time-of-Use), State Inconsistency
- **Description:**
  In `game_routes.py`, the `defend()` route updates the number of `defending_guards` and `defending_adults`. It verifies that the requested deployment does not exceed the current `guard_count` and `adult_count` in memory. However, the route suffers from a TOCTOU race condition:
  ```python
      # 1. Lock acquired (if AP=0), process_turn executes, then DB COMMIT releases the lock!
      turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=1)
      if not turn_ok:
          ...

      # --- RACE WINDOW ---
      # At this point, the DB lock is released.
      # Another request (e.g., an NPC attack or a concurrent player attack) can lock the park,
      # kill adults/guards, and commit the reduced populations to the DB.
      # -------------------

      # 2. Time-of-Check: Checks in-memory (potentially stale) values.
      if num_guards > park.guard_count or num_adults > park.adult_count:
          ...

      # 3. Time-of-Use: Updates memory and commits to DB.
      park.defending_guards = num_guards
      park.defending_adults = num_adults
      db.session.commit()
  ```
  Because `consume_turn` commits its transaction and releases the `with_for_update` lock, the execution window between `consume_turn` returning and the final `db.session.commit()` in the route is completely unprotected. If the actual `adult_count` is reduced below `num_adults` during this window, the final `commit()` will successfully write `defending_adults = num_adults` into the DB. This bypasses all population constraints and creates "Phantom Defenders", allowing `defending_adults` to be greater than `adult_count`.
- **Impact:**
  - Allows `defending_guards` and `defending_adults` to exceed the actual `guard_count` and `adult_count`.
  - Violates the core engine constraint (`defending_* <= *_count`).
  - Allows players to exploit the system by retaining defensive power they do not actually possess.
- **Remediation Recommendation:**
  Use an atomic `UPDATE` query with `case()` statements to strictly bound the `defending_*` values to the current `*_count` in the DB at the exact moment of execution.
  ```python
  Park.query.filter(Park.id == park.id).update({
      'defending_guards': case((Park.guard_count < num_guards, Park.guard_count), else_=num_guards),
      'defending_adults': case((Park.adult_count < num_adults, Park.adult_count), else_=num_adults)
  })
  db.session.commit()
  ```

## 4. Conclusion
The audit discovered a critical TOCTOU race condition in the `/defend` route (`[STATE-F013]`). The `consume_turn` function properly locks and commits, but this premature commit releases the lock before the route applies its business logic, exposing a race window. This allows the creation of "Phantom Defenders". The issue can be resolved by using SQLAlchemy atomic `UPDATE` with clamping logic. No modifications were made during this audit.

---

## 5. 패치 내역 (Fixes Applied)

### [FIXED] STATE-F013 — TOCTOU Race Condition in `/defend` Route (Phantom Defense Exploit)
- **파일**: `app/routes/game_routes.py`
- **조치**: `defend()`의 `park.defending_guards = num_guards` / `park.defending_adults = num_adults` 메모리 할당을, 원자적 `UPDATE` + `case()` 클램핑으로 교체:
  ```python
  Park.query.filter(Park.id == park.id).update({
      'defending_guards': case((Park.guard_count < num_guards, Park.guard_count), else_=num_guards),
      'defending_adults': case((Park.adult_count < num_adults, Park.adult_count), else_=num_adults)
  })
  ```
- **효과**: `consume_turn()`이 커밋하고 띅을 해제한 후, 다른 요청이 인구를 감소시켜도 `defending_*`는 DB의 실제 `*_count`를 초과하지 않음. TOCTOU 윈도우 완전 제거, Phantom Defender Exploit 해소.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
