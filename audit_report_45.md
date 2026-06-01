# JissouParkEmpire Audit Report - Turn 45

## 1. Audit Target
- **Target Module:** `app/routes/auth_routes.py`
- **Target Routes/Functions:** `/register` (`register`)
- **Audit Focus:** Concurrency, TOCTOU, Exception Handling during Registration

## 2. Methodology
- **Audit Type:** Logic Flow Analysis, Concurrency and Exception Handling Review.
- **Reference Standard:** `AI_AUDIT_DOC_STANDARD.md`
- **Execution:**
  1. Examined the changes made to `auth_routes.py` in recent updates (specifically the fix for `[STATE-F014]`).
  2. Analyzed the execution flow of `register()` under concurrent requests using identical `username` or `park_name`.
  3. Identified how the database unique constraint validations are handled.

## 3. Findings

### 3.1. [STATE-F018] Unhandled IntegrityError during User Registration (500 Internal Server Error)
- **Severity:** Medium (Service Stability / Unhandled Exception)
- **Vulnerability Type:** Race Condition (TOCTOU), Missing Error Handling
- **Description:**
  In `auth_routes.py`'s `register()` function, the application attempts to prevent duplicate `username` and `park_name` by performing a `SELECT` check (`User.query.filter_by...`). However, under concurrent registration attempts (TOCTOU race condition), two users can pass the `SELECT` check simultaneously.

  When this happens, the following code is executed:
  ```python
      # 사용자 생성
      user = User(username=username)
      user.set_password(password)
      db.session.add(user)
      db.session.flush()  # <--- [!] 500 Error Point
  ```
  Since `User.username` has a database-level `UNIQUE` constraint, the `db.session.flush()` call will immediately raise an `IntegrityError` if the username is a duplicate.

  While the developer added a `try...except` block lower down to catch exceptions during `db.session.commit()` (intended to handle `Park.name` duplicates), the `db.session.flush()` call is completely unprotected. Consequently, if the race condition occurs on the `username`, the application crashes with an unhandled 500 Internal Server Error.

  Furthermore, the `try...except` block around `commit()` hardcodes the error message:
  ```python
      try:
          db.session.commit()
      except Exception:
          db.session.rollback()
          flash(get_text('flash.reg_parkname_dup'), 'error') # Misleading
          return render_template('register.html')
  ```
  If `commit()` fails for any other database reason, it inaccurately informs the user that the "park name is duplicated."
- **Impact:**
  - Concurrent registrations with the same username will cause an unhandled 500 Internal Server Error.
  - Hardcoded exception handling misinforms users about the root cause of registration failures.
- **Remediation Recommendation:**
  1. Wrap the entire database insertion block (from `db.session.add(user)` down to `db.session.commit()`) in a single `try...except` block to catch `IntegrityError` at any stage (including `flush`).
  2. In the `except` block, analyze the exception message (or rely on the fact that if it fails, it's a duplication of either username or park name) and provide a generic or specifically parsed error message (e.g., "이미 사용 중인 아이디이거나 공원 이름입니다.").

## 4. Remediation

### 4.1. [STATE-F018] Fix Details
- **Modified Files:** `app/routes/auth_routes.py`
- **Change Summary:**
  - Wrapped the entire database insertion block (from `db.session.add(user)` through `db.session.commit()`) in a single `try...except IntegrityError` block.
  - Removed the standalone `try...except` around `db.session.commit()` that previously hardcoded the misleading `flash.reg_parkname_dup` message.
  - Added `from sqlalchemy.exc import IntegrityError` import.
  - On `IntegrityError`, the transaction is rolled back and a generic, accurate duplicate error message (`flash.reg_duplicate`) is flashed to the user.
  - The existing `SELECT`-based duplicate checks (`User.query.filter_by`, `Park.query.filter_by`) are retained for fast-path failure on non-race conditions.

## 5. Conclusion
The unhandled `IntegrityError` vulnerability (`[STATE-F018]`) has been resolved. Concurrent registration attempts that trigger a database unique constraint violation are now gracefully handled with a user-friendly error message, preventing 500 Internal Server Errors.
