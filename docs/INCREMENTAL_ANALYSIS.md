# Incremental Analysis Feature

## Overview

Eidolon's **Incremental Analysis** feature significantly reduces analysis time by intelligently analyzing only the files that have changed since the last analysis or a specified git reference. This is particularly valuable for large codebases where full re-analysis would be time-consuming and wasteful.

## Key Benefits

🚀 **Speed**: Only analyze changed files instead of the entire codebase
💾 **Efficiency**: Preserves cache for unchanged code
📊 **Smart Tracking**: Automatically detects what changed using git
🔄 **Flexible**: Compare against last analysis, specific commits, or branches

## How It Works

### Git Integration

Incremental analysis leverages git to detect file changes:

1. **Change Detection**: Uses `git diff` to identify modified, added, and deleted files
2. **Smart Filtering**: Only Python files (`.py`) are considered for analysis
3. **Base Reference**: Compares against:
   - Last analysis session (default)
   - Specific git commit
   - Specific git branch
   - HEAD (current state)

### Analysis Flow

```
1. Check if directory is a git repository
   ↓
2. Get current git commit and branch
   ↓
3. Determine base reference for comparison
   ↓
4. Detect changed Python files
   ↓
5. Filter modules to analyze (only changed files)
   ↓
6. Invalidate cache for deleted files
   ↓
7. Run parallel analysis on changed modules
   ↓
8. Track statistics and update session
```

### Session Tracking

Each incremental analysis creates a session record that tracks:

- **Session ID**: Unique identifier for the analysis run
- **Git Metadata**: Current commit, branch, base reference
- **File Statistics**: Which files were analyzed vs. skipped
- **Performance Metrics**: Cache hits/misses, module/function counts
- **Timestamps**: When analysis started and completed

This historical data enables future incremental analyses to automatically compare against the last run.

## API Usage

### Endpoint

```
POST /api/analyze/incremental
```

### Request Body

```json
{
  "path": "/path/to/codebase",
  "base": "optional-git-reference"  // Optional: commit hash, branch name, or "HEAD"
}
```

### Response

```json
{
  "status": "completed",
  "mode": "incremental",
  "session_id": "uuid-v4",
  "git_info": {
    "commit": "abc123...",
    "branch": "main",
    "base_reference": "HEAD~5"
  },
  "changes": {
    "modified": 3,
    "added": 1,
    "deleted": 0
  },
  "stats": {
    "files_analyzed": 4,
    "files_skipped": 156,
    "modules_analyzed": 4,
    "functions_analyzed": 23,
    "cache_hits": 312,
    "cache_misses": 23,
    "errors": 0
  },
  "cards_created": 2,
  "hierarchy": { /* agent hierarchy tree */ }
}
```

### Error Handling

If the path is not a git repository:

```json
{
  "error": "Not a git repository. Incremental analysis requires git.",
  "suggestion": "Run full analysis instead, or initialize git repository."
}
```

## Architecture

### Components

#### 1. GitManager (`backend/git_integration/__init__.py`)

**Purpose**: Interface with git to detect changes

**Key Methods**:
- `is_git_repo()`: Verify directory is a git repository
- `get_current_commit()`: Get current HEAD commit hash
- `get_current_branch()`: Get current branch name
- `get_changed_files(base)`: Get all changed files compared to base reference
- `get_changed_python_files(base)`: Get only changed `.py` files

**Data Structures**:
```python
@dataclass
class GitChanges:
    modified: List[str]      # Modified files
    added: List[str]         # New files
    deleted: List[str]       # Deleted files
    renamed: Dict[str, str]  # Old path → New path
    all_changed: List[str]   # All non-deleted changes
```

#### 2. Database Session Tracking (`backend/storage/database.py`)

**New Table**: `analysis_sessions`

```sql
CREATE TABLE analysis_sessions (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    mode TEXT NOT NULL,          -- 'full' or 'incremental'
    git_commit TEXT,
    git_branch TEXT,
    files_analyzed TEXT,          -- JSON array
    files_skipped TEXT,           -- JSON array
    total_modules INTEGER,
    total_functions INTEGER,
    cache_hits INTEGER,
    cache_misses INTEGER,
    created_at TEXT NOT NULL,
    completed_at TEXT
)
```

**Key Methods**:
- `create_analysis_session()`: Create new session record
- `update_analysis_session()`: Update with completion statistics
- `get_last_analysis_session()`: Retrieve most recent completed session

#### 3. Orchestrator (`backend/agents/orchestrator.py`)

**New Method**: `analyze_incremental(path, base=None)`

**Workflow**:
1. Initialize GitManager and verify git repository
2. Get current git metadata (commit, branch)
3. Retrieve last analysis session or use provided base
4. Detect changed Python files using GitManager
5. Filter all modules to only changed files
6. Invalidate cache for deleted files
7. Deploy module agents in parallel (only for changed modules)
8. Run system-level analysis on changed modules
9. Track and return comprehensive statistics

#### 4. API Routes (`backend/api/routes.py`)

**New Endpoint**: `POST /analyze/incremental`

**Features**:
- Path validation and sanitization (security)
- WebSocket progress broadcasts
- Error handling for non-git repositories
- Returns detailed statistics and hierarchy

## Performance Comparison

### Example: Large Codebase (500 files)

| Scenario | Full Analysis | Incremental Analysis | Time Saved |
|----------|---------------|----------------------|------------|
| 2 files changed | 500 files analyzed | 2 files analyzed | ~99% |
| 10 files changed | 500 files analyzed | 10 files analyzed | ~98% |
| 50 files changed | 500 files analyzed | 50 files analyzed | ~90% |

### Cache Benefits

Incremental analysis works seamlessly with Eidolon's caching system:

- **Unchanged files**: Results served from cache (instant)
- **Changed files**: Re-analyzed and cache updated
- **Deleted files**: Cache entries automatically invalidated

## Use Cases

### 1. Continuous Integration (CI)

Run incremental analysis on every commit to only check modified code:

```bash
# Analyze changes since main branch
POST /api/analyze/incremental
{
  "path": "/workspace/repo",
  "base": "origin/main"
}
```

### 2. Development Workflow

Developers can quickly re-analyze after making changes:

```bash
# Analyze uncommitted changes
POST /api/analyze/incremental
{
  "path": "/home/user/project",
  "base": "HEAD"
}
```

### 3. Pull Request Review

Analyze only the files changed in a PR:

```bash
# Analyze changes since PR base branch
POST /api/analyze/incremental
{
  "path": "/repo",
  "base": "origin/develop"
}
```

### 4. Post-Merge Analysis

After merging code, analyze only what changed:

```bash
# Analyze changes since last merge
POST /api/analyze/incremental
{
  "path": "/repo",
  "base": "HEAD~10"
}
```

## Implementation Details

### File Matching Algorithm

The orchestrator matches git changes to Python modules using path comparison:

```python
changed_file_set = set(git_changes.all_changed)
modules_to_analyze = [
    m for m in all_modules
    if any(Path(m.file_path).samefile(path_obj / changed_file)
           for changed_file in changed_file_set
           if (path_obj / changed_file).exists())
]
```

This ensures:
- Exact file matching using `samefile()` (handles symlinks, relative paths)
- Only existing files are considered (handles deleted files gracefully)
- Module objects are matched to git change paths

### Cross-File Dependencies

Even in incremental mode, the **full call graph** is built:

```python
# Use all modules for complete graph, not just changed ones
self.call_graph = self.analyzer.build_call_graph(all_modules)
```

This ensures that:
- Cross-file dependencies are still detected
- Cards created reference the correct files
- System-level patterns are identified

However, only **changed modules** are deeply analyzed with AI agents.

### Cache Invalidation

Deleted files are explicitly removed from cache:

```python
for deleted_file in git_changes.deleted:
    if self.cache:
        await self.cache.invalidate_file(str(path_obj / deleted_file))
```

This prevents stale cache entries for non-existent files.

## Limitations

### 1. Requires Git Repository

Incremental analysis only works in git repositories. For non-git projects, fall back to full analysis:

```python
if not git_manager.is_git_repo():
    return {
        'error': 'Not a git repository',
        'suggestion': 'Run full analysis instead'
    }
```

### 2. Only Detects File-Level Changes

The system detects changed **files**, not changed **functions** within files. If a file changed, all functions in that file are re-analyzed.

Future enhancement: Parse git diffs to identify changed functions only.

### 3. Requires Clean Git State

Uncommitted changes are detected, but the analysis works best with committed code. For pre-commit analysis, compare against `HEAD`.

## Testing

The git integration includes comprehensive test coverage:

```bash
python3 test_git_integration.py
```

**Test Coverage**:
- ✅ Git repository detection
- ✅ Current commit/branch retrieval
- ✅ Changed file detection
- ✅ Python file filtering
- ✅ Multiple base reference support
- ✅ Renamed file handling
- ✅ Deleted file detection

## Future Enhancements

### 1. Function-Level Change Detection

Analyze only changed functions within a file:

```python
# Parse git diff to find changed line ranges
# Map line ranges to function definitions
# Only analyze changed functions
```

### 2. Smart Dependency Analysis

Automatically re-analyze functions that depend on changed functions:

```python
# If function A changed and function B calls A
# Re-analyze both A and B
```

### 3. Multi-Repository Support

Support monorepos with multiple projects:

```python
# Detect which sub-project changed
# Only analyze that sub-project
```

### 4. Performance Visualization

Show visual diff of analysis before/after:

```
Files analyzed:    500 → 5   (99% reduction)
Time taken:        10m → 30s  (95% faster)
Cache efficiency:  95% hit rate
```

## Configuration

Currently, incremental analysis uses sensible defaults. Future configuration options:

```yaml
incremental_analysis:
  enabled: true
  default_base: "last_analysis"  # or "HEAD", "origin/main", etc.
  auto_invalidate_cache: true
  include_dependencies: false    # Future: analyze dependent functions
```

## Troubleshooting

### "Not a git repository" Error

**Problem**: The analyzed directory is not a git repository.

**Solution**:
1. Initialize git: `git init`
2. Or use full analysis instead: `POST /api/analyze`

### No Files Detected as Changed

**Problem**: Incremental analysis reports 0 changed files.

**Possible Causes**:
1. All changes were committed and base is `HEAD`
2. Base reference is the current commit
3. Only non-Python files changed

**Solution**:
- Check git status: `git status`
- Verify base reference
- Use full analysis if needed

### Cache Not Being Used

**Problem**: High cache miss rate in incremental analysis.

**Possible Causes**:
1. First run after clearing cache
2. Cache was invalidated
3. File contents changed significantly

**Solution**: This is expected behavior - incremental analysis will update cache for changed files.

## Monitoring

Track incremental analysis effectiveness using session statistics:

```python
# Query last N sessions
sessions = await db.execute("""
    SELECT
        files_analyzed,
        files_skipped,
        cache_hits,
        cache_misses,
        created_at
    FROM analysis_sessions
    ORDER BY created_at DESC
    LIMIT 10
""")

# Calculate efficiency
for session in sessions:
    efficiency = session.cache_hits / (session.cache_hits + session.cache_misses)
    print(f"Cache efficiency: {efficiency:.1%}")
```

## Conclusion

Incremental Analysis makes Eidolon practical for large codebases and continuous integration workflows. By leveraging git and intelligent caching, analysis time is reduced by 90-99% for typical development workflows where only a small portion of code changes between runs.
