# MONAD → Eidolon Migration Checklist

**Generated:** 2025-11-24
**Total Occurrences:** 228 references across 53 files
**Status:** Ready for execution

---

## Summary

**Files to Update:** 53 total
- **Critical (Production Code):** 15 files
- **High Priority (Documentation):** 11 files
- **Medium Priority (Tests):** 13 files
- **Low Priority (Config/Other):** 14 files

**File to Rename:** 1 file
- `test_monad_repo.py` → `test_eidolon_repo.py`

---

## Critical Priority - Production Code (15 files)

**Impact:** User-facing, database, metrics, API
**Risk:** High if incorrect
**Estimated Time:** 30 minutes

### Backend Python Files

| File | Occurrences | Changes Needed |
|------|-------------|----------------|
| `src/eidolon/metrics/__init__.py` | 47 | **CRITICAL** - All Prometheus metric names (monad_*) |
| `src/eidolon/main.py` | 5 | FastAPI app title, description, database name |
| `src/eidolon/storage/database.py` | 3 | Database comments, logging |
| `src/eidolon/cache/cache_manager.py` | 2 | Comments, logging |
| `src/eidolon/api/routes.py` | 1 | Comments or strings |
| `src/eidolon/code_writer.py` | 1 | Comments or strings |
| `src/eidolon/db_pool.py` | 1 | Comments or strings |
| `src/eidolon/health/__init__.py` | 1 | Comments or strings |
| `src/eidolon/llm_providers/__init__.py` | 1 | Comments in docstrings |
| `src/eidolon/logging_config.py` | 1 | Comments or config |
| `src/eidolon/models/card.py` | 1 | ID prefix or comments |
| `src/eidolon/request_context.py` | 1 | Comments |
| `src/eidolon/resilience/__init__.py` | 1 | Comments |
| `src/eidolon/resource_limits.py` | 1 | Comments |
| `src/eidolon/test_cache.py` | 1 | Test file (could move to tests/) |

**Action Items:**
1. ✅ Update `main.py` database name: `monad.db` → `eidolon.db`
2. ✅ Update `main.py` FastAPI title/description
3. ⚠️ **IMPORTANT:** Update all Prometheus metrics in `metrics/__init__.py`:
   - `monad_*` → `eidolon_*` (47 occurrences)
   - This will break existing Grafana dashboards - document breaking change
4. ✅ Update comments/docstrings in remaining files

### Frontend Files

| File | Occurrences | Changes Needed |
|------|-------------|----------------|
| `frontend/src/components/TopNav.vue` | 1 | App title or branding |
| `frontend/index.html` | 1 | Title tag |
| `frontend/package.json` | 2 | Project name, description |
| `frontend/package-lock.json` | 2 | Auto-updated when package.json changes |

**Action Items:**
1. ✅ Update `index.html` `<title>` tag
2. ✅ Update `package.json` name and description
3. ✅ Update TopNav.vue branding
4. ✅ Run `npm install` to regenerate package-lock.json

---

## High Priority - Documentation (11 files)

**Impact:** Developer onboarding, understanding
**Risk:** Low (cosmetic)
**Estimated Time:** 20 minutes

| File | Occurrences | Purpose |
|------|-------------|---------|
| `README.md` | 4 | Main project README |
| `AGENTS.md` | 1 | Agent guidelines |
| `docs/ARCHITECTURE.md` | 3 | Architecture documentation |
| `docs/MVP_SUMMARY.md` | 5 | MVP summary |
| `MULTI_PROVIDER_GUIDE.md` | 12 | LLM provider guide |
| `LLM_CONNECTION_ARCHITECTURE.md` | 14 | LLM architecture |
| `RELIABILITY_IMPLEMENTATION_PLAN.md` | 20 | Reliability planning |
| `AGENT_HIERARCHY.md` | 2 | Agent hierarchy docs |
| `INCREMENTAL_ANALYSIS.md` | 3 | Incremental analysis |
| `UX_REVIEW.md` | 3 | UX review notes |
| `.env.example` | 1 | Environment variable example |

**Action Items:**
1. ✅ Global search-replace `MONAD` → `Eidolon` in all .md files
2. ✅ Update README.md header and description
3. ✅ Update .env.example comments if needed
4. ✅ Review ARCHITECTURE.md (may want to replace with new arch-analysis diagrams)

---

## Medium Priority - Test Files (13 files)

**Impact:** Test execution, CI/CD
**Risk:** Low (tests still work)
**Estimated Time:** 15 minutes

| File | Occurrences | Action |
|------|-------------|--------|
| `test_monad_repo.py` | 8 | **RENAME FILE** to `test_eidolon_repo.py` + update content |
| `test_gemini_enhancements.py` | 11 | Update references |
| `test_rest_api_implementation.py` | 5 | Update references |
| `test_gemini_advanced.py` | 4 | Update references |
| `test_calculator_implementation.py` | 3 | Update references |
| `test_with_real_llm.py` | 3 | Update references |
| `test_end_to_end_calculator.py` | 2 | Update references |
| `test_orchestrator_end_to_end.py` | 2 | Update references |
| `test_top_down_implementation.py` | 2 | Update references |
| `test_5tier_hierarchy.py` | 2 | Update references |
| `tests/test_database.py` | 2 | Update references |
| `tests/test_api_routes.py` | 1 | Update references |
| `src/eidolon/test_parallel.py` | 1 | Move to tests/ + update |

**Action Items:**
1. ✅ Rename `test_monad_repo.py` → `test_eidolon_repo.py`
2. ✅ Global search-replace in all test files
3. ✅ Move `src/eidolon/test_parallel.py` to `tests/` directory
4. ✅ Run tests to verify nothing broke

---

## Low Priority - Analysis & Review Docs (14 files)

**Impact:** Historical records, analysis artifacts
**Risk:** None (informational only)
**Estimated Time:** 5 minutes

| File | Occurrences | Action |
|------|-------------|--------|
| `RELIABILITY_ANALYSIS.md` | 7 | Update or archive |
| `CODE_REVIEW.md` | 1 | Update or archive |
| `GEMINI_ENHANCEMENT_SUGGESTIONS.md` | 1 | Update or archive |
| `LARGE_PROJECT_TEST_RESULTS.md` | 2 | Update or archive |
| `REAL_LLM_TEST_RESULTS.md` | 2 | Update or archive |

**Plus:** 5 files in `docs/arch-analysis-2025-11-24-0510/` (our new analysis)

**Action Items:**
1. ⚠️ **Decision needed:** Keep historical docs as-is (snapshot) OR update them?
2. ✅ Our arch-analysis docs can reference "formerly MONAD" for context
3. ✅ Consider moving old analysis docs to `docs/archive/`

---

## Automated Migration Script

Here's a bash script to automate the core replacements:

```bash
#!/bin/bash
# monad-to-eidolon-migration.sh

set -e

echo "🔄 MONAD → Eidolon Migration Script"
echo "====================================="
echo ""

# Backup
echo "📦 Creating backup..."
tar -czf monad-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  src/ frontend/ tests/ docs/ *.md *.py 2>/dev/null || true
echo "✅ Backup created"
echo ""

# 1. Rename file
echo "📝 Renaming test_monad_repo.py..."
if [ -f "test_monad_repo.py" ]; then
  git mv test_monad_repo.py test_eidolon_repo.py 2>/dev/null || \
    mv test_monad_repo.py test_eidolon_repo.py
  echo "✅ File renamed"
else
  echo "⚠️  test_monad_repo.py not found (may already be renamed)"
fi
echo ""

# 2. Update production code
echo "🔧 Updating production code..."

# Main app
sed -i 's/title="MONAD API"/title="Eidolon API"/g' src/eidolon/main.py
sed -i 's/description="Hierarchical Agent System for Code Analysis"/description="Hierarchical AI Agent System for Code Analysis"/g' src/eidolon/main.py
sed -i 's/monad\.db/eidolon.db/g' src/eidolon/main.py

# Metrics (CRITICAL - breaks dashboards)
sed -i "s/'monad_/'eidolon_/g" src/eidolon/metrics/__init__.py
sed -i 's/"monad_/"eidolon_/g' src/eidolon/metrics/__init__.py

# Database
sed -i 's/MONAD/Eidolon/g' src/eidolon/storage/database.py

# Comments in other files (case-insensitive)
find src/eidolon -name "*.py" -type f -exec sed -i 's/MONAD/Eidolon/g' {} \;
find src/eidolon -name "*.py" -type f -exec sed -i 's/monad/eidolon/g' {} \;

echo "✅ Production code updated"
echo ""

# 3. Update frontend
echo "🎨 Updating frontend..."

sed -i 's/MONAD/Eidolon/g' frontend/index.html
sed -i 's/"monad"/"eidolon"/g' frontend/package.json
sed -i 's/MONAD/Eidolon/g' frontend/src/components/TopNav.vue

echo "✅ Frontend updated"
echo ""

# 4. Update documentation
echo "📚 Updating documentation..."

sed -i 's/MONAD/Eidolon/g' README.md
sed -i 's/# monad/# eidolon/i' README.md
sed -i 's/MONAD/Eidolon/g' AGENTS.md
sed -i 's/MONAD/Eidolon/g' docs/ARCHITECTURE.md
sed -i 's/MONAD/Eidolon/g' docs/MVP_SUMMARY.md
sed -i 's/MONAD/Eidolon/g' *.md

echo "✅ Documentation updated"
echo ""

# 5. Update tests
echo "🧪 Updating tests..."

find tests -name "*.py" -type f -exec sed -i 's/monad/eidolon/gi' {} \;
find . -maxdepth 1 -name "test_*.py" -type f -exec sed -i 's/monad/eidolon/gi' {} \;

echo "✅ Tests updated"
echo ""

# 6. Regenerate frontend dependencies
echo "📦 Regenerating frontend package-lock.json..."
cd frontend
npm install
cd ..
echo "✅ Frontend dependencies updated"
echo ""

echo "✅ MIGRATION COMPLETE!"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "1. Review changes: git diff"
echo "2. Test the application: uv run uvicorn eidolon.main:app --reload"
echo "3. Run tests: uv run pytest tests/"
echo "4. Update Grafana dashboards (metrics renamed: monad_* → eidolon_*)"
echo "5. Commit changes: git add . && git commit -m 'Rename MONAD → Eidolon'"
echo ""
echo "📊 Backup location: monad-backup-*.tar.gz"
```

**To run:**
```bash
chmod +x monad-to-eidolon-migration.sh
./monad-to-eidolon-migration.sh
```

---

## Manual Migration Steps (Safer)

If you prefer manual control:

### Step 1: Database File (CRITICAL)

```bash
# Update main.py
sed -i 's/monad\.db/eidolon.db/g' src/eidolon/main.py

# If you have existing monad.db, migrate data:
cp monad.db eidolon.db
```

### Step 2: Metrics (BREAKING CHANGE)

```bash
# Update all Prometheus metrics
sed -i "s/'monad_/'eidolon_/g" src/eidolon/metrics/__init__.py
sed -i 's/"monad_/"eidolon_/g' src/eidolon/metrics/__init__.py

# ⚠️ WARNING: This breaks existing Grafana dashboards
# You'll need to update dashboard queries: monad_* → eidolon_*
```

### Step 3: FastAPI App

```bash
# Update app metadata
sed -i 's/title="MONAD API"/title="Eidolon API"/g' src/eidolon/main.py
```

### Step 4: Frontend

```bash
# Update branding
sed -i 's/MONAD/Eidolon/g' frontend/index.html
sed -i 's/"monad"/"eidolon"/g' frontend/package.json
sed -i 's/MONAD/Eidolon/g' frontend/src/components/TopNav.vue

# Regenerate package-lock.json
cd frontend && npm install && cd ..
```

### Step 5: Documentation

```bash
# Update all markdown files
for file in *.md docs/*.md; do
  sed -i 's/MONAD/Eidolon/g' "$file"
done
```

### Step 6: Tests

```bash
# Rename file
git mv test_monad_repo.py test_eidolon_repo.py

# Update references in all tests
find tests -name "*.py" -exec sed -i 's/monad/eidolon/gi' {} \;
find . -maxdepth 1 -name "test_*.py" -exec sed -i 's/monad/eidolon/gi' {} \;
```

---

## Verification Checklist

After migration, verify:

- [ ] App starts: `uv run uvicorn eidolon.main:app --reload`
- [ ] Database created as `eidolon.db` (not `monad.db`)
- [ ] Frontend shows "Eidolon" in title bar
- [ ] API docs show "Eidolon API" at http://localhost:8000/docs
- [ ] Tests pass: `uv run pytest tests/`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Metrics endpoint works: http://localhost:8000/metrics
- [ ] No references to "monad" in user-facing UI
- [ ] README.md updated
- [ ] Git commit created with changes

---

## Breaking Changes

**⚠️ IMPORTANT:** This migration includes breaking changes:

### 1. Database File Name
- **Old:** `monad.db`
- **New:** `eidolon.db`
- **Impact:** Existing data will not be loaded unless you rename/migrate
- **Mitigation:** `cp monad.db eidolon.db` before first run

### 2. Prometheus Metrics
- **Old:** `monad_*` (e.g., `monad_analyses_total`, `monad_ai_api_calls_total`)
- **New:** `eidolon_*` (e.g., `eidolon_analyses_total`, `eidolon_ai_api_calls_total`)
- **Impact:** Existing Grafana dashboards will break
- **Mitigation:** Update all dashboard queries to use new metric names

### 3. API Title
- **Old:** "MONAD API"
- **New:** "Eidolon API"
- **Impact:** OpenAPI docs title changes (cosmetic only)

---

## Rollback Plan

If migration fails:

```bash
# Restore from backup
tar -xzf monad-backup-*.tar.gz

# Or use git
git checkout .
git clean -fd
```

---

## Timeline Estimate

| Task | Time | Priority |
|------|------|----------|
| Production code updates | 30 min | Critical |
| Documentation updates | 20 min | High |
| Test file updates | 15 min | Medium |
| Frontend npm install | 5 min | Critical |
| Verification testing | 15 min | Critical |
| **Total** | **~90 min** | |

---

## Post-Migration Tasks

After successful migration:

1. **Update CHANGELOG.md:**
   ```markdown
   ## [0.2.0] - 2025-11-24
   ### Changed
   - **BREAKING:** Renamed project from MONAD to Eidolon
   - **BREAKING:** Database file renamed: monad.db → eidolon.db
   - **BREAKING:** Prometheus metrics renamed: monad_* → eidolon_*
   - Updated all documentation and branding
   ```

2. **Update Grafana Dashboards:**
   - Export existing dashboards
   - Search-replace `monad_` → `eidolon_`
   - Re-import dashboards

3. **Notify Team:**
   - Send migration guide to team
   - Update deployment scripts
   - Update monitoring/alerting

4. **Archive Old Docs:**
   ```bash
   mkdir -p docs/archive/monad-era
   mv RELIABILITY_ANALYSIS.md docs/archive/monad-era/
   mv CODE_REVIEW.md docs/archive/monad-era/
   # etc.
   ```

---

## Summary

**Total Work:**
- 53 files to update
- 228 occurrences to change
- 1 file to rename
- ~90 minutes estimated time
- 2 breaking changes (database name, metrics)

**Recommendation:** Use the automated script for speed, but review diffs carefully before committing.

**Alternative:** Manual migration using Step-by-Step guide for maximum control.

---

**Ready to Execute?** Run the migration script or follow manual steps above.
