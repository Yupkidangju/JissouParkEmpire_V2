# Audit Report 56

## Target
- `app/game_engine.py` (consume_turn, action_points, process_turn)
- `app/npc_engine.py` (_sync_npc_turns)

## Findings

### 1. [STATE-F029] Race Condition in `consume_turn` slow path leading to Action Points (AP) duplication (Lost Update)
- **Severity**: High
- **Description**:
  - The `consume_turn` function handles two paths: a fast-path that atomically deducts AP if `turn_quota` is not needed, and a slow path that consumes a `turn_quota`, refills AP, runs `process_turn()`, and synchronizes NPC turns via `_sync_npc_turns()`.
  - In the slow path, after `process_turn(park)` finishes, it explicitly calls `db.session.commit()`, which releases the pessimistic lock on the `park` object.
  - Then, it calls `_sync_npc_turns(park)`. This function can take a significant amount of time as it loops through all NPCs, acquires locks for each, processes their turns, and commits them.
  - During this execution gap where the lock on `park` is released, the user can fire concurrent HTTP requests (e.g., `action_gather`, `action_cull`). These requests will hit the fast-path because the AP was just refilled to `GC.ACTION_POINTS_PER_TURN` (10) in the database by `process_turn()`. They will successfully deduct AP atomically and commit.
  - Finally, when `_sync_npc_turns` finishes, the original slow-path thread executes `park.action_points -= ap_cost` in memory (non-atomically) and commits this state with `db.session.commit()`.
  - Because it relies on the stale memory state (or state refreshed before the concurrent transactions finished) and does not perform an atomic update for the final AP deduction, it overwrites the `action_points` value in the database, effectively erasing the AP consumed by the concurrent fast-path requests.
- **Impact**:
  - A malicious user can exploit this race window to execute multiple actions (like `action_gather`) for free, bypassing the intended AP cost constraints and duplicating AP usage.
- **Location**: `app/game_engine.py:163` (inside `consume_turn` where `park.action_points -= ap_cost` is performed without an atomic `UPDATE`).
