# Phase 2 Testing Plan

## Overview
Comprehensive testing strategy to ensure Phase 2 (File I/O, Testing, Rollback) is production-ready before implementing Phase 3 (Negotiation).

## Test Categories

### 1. Task Type Tests
- [ ] **CREATE_NEW**: Create new functions/classes/modules from scratch
- [ ] **MODIFY_EXISTING**: Modify existing code without breaking it
- [ ] **REFACTOR**: Improve code structure while preserving behavior
- [ ] **DELETE**: Remove unused code safely
- [ ] **FIX**: Fix bugs in existing code
- [ ] **TEST**: Generate test coverage for existing code

### 2. Hierarchy Tests
- [ ] **FUNCTION level**: Simple function creation and modification
- [ ] **CLASS level**: Class with multiple methods
- [ ] **MODULE level**: Module with multiple classes/functions
- [ ] **SUBSYSTEM level**: Directory with multiple modules
- [ ] **SYSTEM level**: Full project decomposition

### 3. Dependency Tests
- [ ] **Sequential dependencies**: Task B depends on Task A
- [ ] **Parallel execution**: Independent tasks run concurrently
- [ ] **Complex DAG**: Multiple dependencies (A→B→D, A→C→D)
- [ ] **Circular dependency detection**: Prevent deadlocks
- [ ] **Cross-module dependencies**: Function in module A calls function in module B

### 4. File I/O Tests
- [ ] **Create new file**: Write to non-existent file
- [ ] **Modify existing file**: Append/replace in existing file
- [ ] **Backup creation**: Verify backups are created
- [ ] **Atomic writes**: Temp file → rename pattern
- [ ] **Directory creation**: Auto-create missing directories
- [ ] **File conflicts**: Multiple writes to same file
- [ ] **Large files**: Performance with big codebases

### 5. Test Generation Tests
- [ ] **Simple function**: Basic input/output test
- [ ] **Edge cases**: None, empty, boundary values
- [ ] **Error cases**: Exception handling tests
- [ ] **Complex logic**: Multiple paths and conditions
- [ ] **Dependencies**: Mocking external dependencies
- [ ] **Integration tests**: Class/module level tests

### 6. Rollback Tests
- [ ] **Test failure rollback**: Revert when tests fail
- [ ] **Partial rollback**: Some tasks succeed, some fail
- [ ] **Multi-file rollback**: Rollback multiple changed files
- [ ] **Nested task rollback**: Parent fails, children rollback
- [ ] **Backup restoration**: Verify files restored correctly

### 7. Error Handling Tests
- [ ] **Missing files**: Task references non-existent file
- [ ] **Syntax errors**: Generated code has syntax errors
- [ ] **Import errors**: Missing dependencies
- [ ] **Timeout**: Long-running tasks
- [ ] **LLM failures**: API errors, invalid JSON responses
- [ ] **Disk full**: Can't write files
- [ ] **Permission errors**: Can't write to directory

### 8. Mock LLM Tests
- [ ] **JSON parsing**: Valid JSON responses
- [ ] **Fallback responses**: Handle parse failures gracefully
- [ ] **Realistic code generation**: Generated code is valid Python
- [ ] **Test generation quality**: Tests actually test the code
- [ ] **Consistency**: Same input → similar output

### 9. Performance Tests
- [ ] **Small project**: < 10 files, fast completion
- [ ] **Medium project**: 50-100 files
- [ ] **Large project**: 500+ files
- [ ] **Concurrent task limits**: max_concurrent_tasks tuning
- [ ] **Memory usage**: No memory leaks
- [ ] **Database performance**: Fast task/agent queries

### 10. Integration Tests
- [ ] **End-to-end flow**: User request → working code
- [ ] **Real project**: Test on actual open-source project
- [ ] **Multi-tier decomposition**: All 5 tiers working together
- [ ] **Full pipeline**: Planning → Execution → Testing → Rollback
- [ ] **State persistence**: Database correctly stores all state

## Test Projects

### Test Project 1: Simple Calculator (Baseline)
- **Purpose**: Validate basic functionality
- **Structure**: Single module, multiple functions
- **Tasks**: CREATE_NEW functions (add, subtract, multiply, divide)

### Test Project 2: REST API (Realistic)
- **Purpose**: Test multi-tier hierarchy
- **Structure**:
  - `api/` - FastAPI routes
  - `services/` - Business logic
  - `models/` - Data models
  - `utils/` - Helpers
- **Tasks**: Add authentication feature (multi-subsystem)

### Test Project 3: Existing Codebase (Modification)
- **Purpose**: Test MODIFY_EXISTING and REFACTOR
- **Structure**: Pre-existing code with tests
- **Tasks**: Refactor for better structure

### Test Project 4: Broken Code (Fix)
- **Purpose**: Test FIX task type
- **Structure**: Code with known bugs
- **Tasks**: Fix bugs one by one

### Test Project 5: Large Codebase (Performance)
- **Purpose**: Test scalability
- **Structure**: 100+ files, complex dependencies
- **Tasks**: Add cross-cutting feature

## Success Criteria

### Must Pass (Blocking)
1. ✅ All task types work correctly
2. ✅ File I/O is atomic and safe
3. ✅ Rollback fully restores previous state
4. ✅ No data loss under any circumstance
5. ✅ Dependencies resolved correctly (no deadlocks)
6. ✅ Generated code is syntactically valid
7. ✅ Tests actually test the generated code

### Should Pass (Important)
1. ⚠️ Test generation produces useful tests
2. ⚠️ Performance acceptable for medium projects (< 5 min)
3. ⚠️ Error messages are clear and actionable
4. ⚠️ Mock LLM responses are realistic
5. ⚠️ Parallel execution improves performance

### Nice to Have (Future)
1. 💡 Large projects complete in reasonable time
2. 💡 Memory usage stays constant
3. 💡 Test coverage > 80%
4. 💡 Code quality metrics improve

## Test Execution Order

1. **Unit Tests**: Test individual components in isolation
   - CodeWriter
   - TestGenerator
   - TestRunner
   - Task graph
   - Each decomposer

2. **Integration Tests**: Test components working together
   - Planning phase (decomposition)
   - Execution phase (code generation)
   - Testing phase (test gen + run)
   - Rollback phase

3. **End-to-End Tests**: Full user workflows
   - Simple project (calculator)
   - Realistic project (REST API)
   - Existing codebase modification
   - Bug fixing workflow

4. **Stress Tests**: Push the limits
   - Large codebase
   - Complex dependencies
   - Concurrent task limits
   - Error recovery

## Bug Tracking

### Known Issues
- [ ] Mock LLM JSON parsing fails frequently (needs better prompting)
- [ ] Empty task lists at CLASS/FUNCTION level (decomposition issue)
- [ ] No actual pytest integration yet (TestRunner not fully implemented)

### Fixed Issues
- [x] `project_path` variable reference (commit 05de28a)
- [x] `priority.value` AttributeError (commit 05de28a)

## Next Steps

1. Create Test Project 1 (Simple Calculator)
2. Run through all task types
3. Verify file I/O and backups
4. Test rollback mechanism
5. Fix bugs as discovered
6. Document all findings
7. Create Test Project 2 (REST API)
8. Iterate until all Must Pass criteria met
