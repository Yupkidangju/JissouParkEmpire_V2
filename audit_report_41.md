# JissouParkEmpire Audit Report - Turn 41

## 1. Audit Target
- **Target Module:** `app/routes/auth_routes.py`
- **Target Functions:** `register()`
- **Audit Focus:** Concurrency and State Consistency (Impersonation via Park Name Duplication)

## 2. Methodology
- **Audit Type:** Source code review, Concurrency analysis.
- **Reference Standard:** `AI_AUDIT_DOC_STANDARD.md`
- **Execution:**
  1. Traced the execution of the `register()` route.
  2. Analyzed the pre-flight checks for `username` and `park_name`.
  3. Correlated the checks with the database constraints defined in `app/models.py`.

## 3. Findings

### 3.1. [STATE-F014] TOCTOU Race Condition in `/register` Route (Park Name Duplication Exploit)
- **Severity:** Medium
- **Vulnerability Type:** Concurrency Issue (Time-of-Check to Time-of-Use), Spoofing/Impersonation
- **Description:**
  In `auth_routes.py`, the `register()` route performs a manual check to ensure the chosen `park_name` is unique:
  ```python
      if Park.query.filter_by(name=park_name).first():
          flash(get_text('flash.reg_parkname_dup'), 'error')
          return render_template('register.html')
  ```
  After this check, it proceeds to create the `User` and `Park` objects, eventually calling `db.session.commit()`.

  However, the `name` column in the `Park` model (`app/models.py`) does NOT have a database-level `unique=True` constraint:
  ```python
      name = db.Column(db.String(100), nullable=False)
  ```
  Because the check is performed in Python space without a database-level lock or unique constraint, a Time-of-Check to Time-of-Use (TOCTOU) race condition exists. If two requests concurrently register the exact same `park_name`, both threads can pass the `if` check simultaneously. Since there is no DB constraint to prevent it, both `Park` entries will be successfully created with the identical name.
- **Impact:**
  - Allows malicious actors to bypass the uniqueness check and create a park with a name identical to an existing park (e.g., top-ranking players or system NPCs).
  - This can be leveraged for social engineering or spoofing attacks in the Trade Market (`/trade`), where other players might be tricked into accepting unfavorable trades thinking they are dealing with a trusted park.
- **Remediation Recommendation:**
  Add a unique constraint to the `Park` model's `name` column at the database level.
  ```python
  # in app/models.py
  name = db.Column(db.String(100), unique=True, nullable=False)
  ```
  Additionally, catch the `sqlalchemy.exc.IntegrityError` during `db.session.commit()` in the `register()` route to gracefully handle the concurrent duplicate registration.

## 4. Conclusion
The audit discovered a TOCTOU race condition in the `/register` route (`[STATE-F014]`). Due to the lack of a database-level unique constraint on `Park.name`, attackers can exploit a race window to create duplicate park names. This enables impersonation and spoofing within the game's social features (like the trade market). The vulnerability can be mitigated by enforcing uniqueness at the database level. No modifications were made during this audit.

---

## 5. 패치 내역 (Fixes Applied)

### [FIXED] STATE-F014 — TOCTOU Race Condition in `/register` Route (Park Name Duplication Exploit)
- **파일**: `app/models.py`, `app/routes/auth_routes.py`
- **조치**:
  1. `Park` 모델의 `name` 컬럼에 `unique=True` 제약을 추가: `name = db.Column(db.String(100), unique=True, nullable=False)`.
  2. `register()` 라우트의 `db.session.commit()`을 `try/except`로 감싸, 동시 중복 등록 시 발생하는 `IntegrityError`를 잡아 우아하게 차단하고 중복 메시지를 표시.
- **효과**: Python 메모리 검사(`Park.query.filter_by(name=park_name).first()`)를 통과한 후에도, DB 레벨 `UNIQUE` 제약이 최종 방어선으로 작동하여 동일 공원명 중복 생성을 원천 차단. impersonation/spoofing 공격 가능성 제거.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
