# Student Lab & Interactive SQL Query Grading System Implementation Plan

This plan establishes an automated grading and challenge system for the Universal Language Architecture & Crosswalk Platform (Option 3). It equips student learners with guided interactive challenges, schema/row evaluation, instant diagnostic feedback, and XP badge progression directly integrated into the curriculum interface.

---

## User Stories & Architecture

### Student Experience:
1. As a student learning compiler/runtime internals through SQL, I can switch between **📖 Theory & Insights** and **🧪 Student Lab Challenge** within any tutoring query.
2. I can read an explicit lab objective, required columns, and minimum row count criteria.
3. I can click **"Load Starter Scaffold"** to replace the SQL editor with a prepared problem skeleton.
4. If stuck, I can reveal progressive hints without giving away the complete solution.
5. I can click **"Test & Grade Solution"**, which executes my query against the active database and provides immediate automated grading (Pass/Fail, XP points, column validation, row count validation, and data parity checks).
6. My solved challenges and earned XP are persisted locally in `localStorage`, celebrating my progress with visual badges (`🏆 Solved (+100 XP)`) and an XP counter in the header.

### Backend Architecture:
1. **Curriculum Schema Extension**: Add optional `lab_challenge` block to SQL YAML frontmatter:
   ```yaml
   lab_challenge:
     objective: "Count the number of containers in each container_kind..."
     starter_sql: "SELECT container_kind, ... FROM containers GROUP BY ...;"
     solution_sql: "SELECT container_kind, COUNT(*) AS container_count FROM containers GROUP BY container_kind ORDER BY container_count DESC;"
     expected_columns: ["container_kind", "container_count"]
     min_rows: 1
     xp_reward: 100
     hint: "Use COUNT(*) and GROUP BY container_kind."
   ```
2. **`QueryLoader`**: Safely extracts `lab_challenge` dictionary in `server/query_loader.py`.
3. **`POST /api/lab/grade` Endpoint**:
   - Request: `{ query_id: str, db_id: str, student_sql: str }`
   - Validates student SQL safely via `DatabaseManager.execute_query`.
   - Runs reference `solution_sql` to determine ground-truth schema and results.
   - Evaluates:
     - SQL execution success (syntax/runtime errors).
     - Column name presence (case-insensitive, e.g. `dist_name`, `container_count`).
     - Minimum & maximum row bounds.
     - Content parity (validates that student query returned the expected semantic records).
   - Returns detailed structured feedback, score (0-100), and `xp_earned`.

---

## Proposed Changes

### 1. Backend: `server/query_loader.py` & `server/routes.py`
- In `server/query_loader.py`:
  - Include `"lab_challenge": metadata.get("lab_challenge")` in returned dictionary.
- In `server/routes.py`:
  - Define `GradeLabRequest` Pydantic model:
    ```python
    class GradeLabRequest(BaseModel):
        query_id: str
        db_id: str
        student_sql: str
    ```
  - Define `POST /api/lab/grade` endpoint:
    - Load query by `query_id`.
    - If `lab_challenge` not present, return 400 error.
    - Execute `student_sql` via `db_manager.execute_query`. If it returns `"error"`, return `{ "passed": false, "score": 0, "feedback": f"SQL Error: {res['error']}" }`.
    - Evaluate columns: check that each column in `expected_columns` exists in `student_cols` (case-insensitive).
    - Evaluate row count: ensure `len(student_rows) >= min_rows`.
    - Evaluate reference `solution_sql` parity if present:
      - Execute reference query.
      - Check row count match and value alignment where applicable.
    - Return passed boolean, score, xp_earned, feedback, and detailed diagnostic checks.

### 2. Curriculum Enrichment: Sample Tutoring Queries
Add `lab_challenge` blocks to representative tutoring queries across multiple languages:
- `queries/python/tutoring/01_strata_and_environments.sql` (Filter Stratum 1 standard library)
- `queries/python/tutoring/02_container_hierarchy.sql` (Group and count containers by kind)
- `queries/csharp/tutoring/01_strata_and_runtime.sql` (Filter C# runtime distributions)
- `queries/rust/tutoring/01_prelude_and_crate_strata.sql` (Filter core and alloc crates)
- `queries/typescript/tutoring/01_ambient_scope_and_node_stdlib.sql` (Ambient scope inspection)

### 3. Frontend: Types, API, & `TutorCard.tsx`
- In `React_UI/src/types.ts`:
  - Add `LabChallenge` interface.
  - Extend `QueryInfo` with `lab_challenge?: LabChallenge`.
  - Add `GradeLabRequest` and `GradeLabResponse` interfaces.
- In `React_UI/src/api.ts`:
  - Add `gradeLabQuery(req: GradeLabRequest): Promise<GradeLabResponse>`.
- In `React_UI/src/components/TutorCard.tsx`:
  - Add mode tabs: `[ 📖 Theory & Insights ]` | `[ 🧪 Student Lab Challenge ]`.
  - In Lab tab:
    - Display Objective card with target criteria badges (`Expected Columns`, `Min Rows`, `XP Reward`).
    - Provide "Load Starter Scaffold" button (sets editor SQL).
    - Provide "Need a Hint?" toggle with progressive hints.
    - Provide "Test & Grade Solution" button that triggers grading API.
    - Render Grade Result Card:
      - Green banner for Passed: `🎉 Solved! +100 XP` with detailed checks.
      - Red/amber banner for Incomplete: Detailed diagnosis explaining missing columns or row count issues.
    - Persist completions to `localStorage.getItem("utss_lab_progress")`.
- In `React_UI/src/components/TopNav.tsx`:
  - Display student total XP badge: `⚡ 100 XP` with tooltip showing completed labs count.

### 4. Automated Tests: `tests/test_lab_api.py`
- Test `POST /api/lab/grade` passing with full points.
- Test `POST /api/lab/grade` failing on SQL syntax error.
- Test `POST /api/lab/grade` failing on missing expected columns.
- Test `POST /api/lab/grade` failing on row count deficit.
- Test 404 on nonexistent query ID or query without lab challenge.

---

## Verification Plan
1. Run `.venv/bin/pytest tests/test_lab_api.py -v` (Sandboxed/BypassSandbox).
2. Run full pytest suite: `.venv/bin/pytest -v`.
3. Compile React UI: `npm --prefix React_UI run build`.
4. Verify end-to-end functionality.
