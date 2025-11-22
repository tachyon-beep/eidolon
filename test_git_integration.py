#!/usr/bin/env python3
"""Quick test script for git integration functionality"""

import sys
sys.path.insert(0, 'backend')

from git_integration import GitManager

def test_git_integration():
    """Test the GitManager class with the current repository"""
    print("Testing Git Integration")
    print("=" * 50)

    # Initialize GitManager for current repo
    git_manager = GitManager('.')

    # Test 1: Check if it's a git repo
    print("\n1. Checking if current directory is a git repository...")
    is_repo = git_manager.is_git_repo()
    print(f"   Is git repo: {is_repo}")
    if not is_repo:
        print("   ERROR: Not a git repository!")
        return False

    # Test 2: Get current commit and branch
    print("\n2. Getting git metadata...")
    try:
        commit = git_manager.get_current_commit()
        branch = git_manager.get_current_branch()
        print(f"   Current commit: {commit[:12]}...")
        print(f"   Current branch: {branch}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    # Test 3: Get changed files since HEAD
    print("\n3. Getting changed files since HEAD...")
    try:
        changes = git_manager.get_changed_files(base='HEAD')
        print(f"   Modified files: {len(changes.modified)}")
        print(f"   Added files: {len(changes.added)}")
        print(f"   Deleted files: {len(changes.deleted)}")
        print(f"   Renamed files: {len(changes.renamed)}")

        if changes.modified:
            print(f"\n   Example modified files:")
            for f in changes.modified[:5]:
                print(f"     - {f}")

        if changes.added:
            print(f"\n   Example added files:")
            for f in changes.added[:5]:
                print(f"     - {f}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    # Test 4: Get changed Python files only
    print("\n4. Getting changed Python files only...")
    try:
        py_changes = git_manager.get_changed_python_files(base='HEAD')
        print(f"   Changed Python files: {len(py_changes.all_changed)}")

        if py_changes.all_changed:
            print(f"\n   Python files that changed:")
            for f in py_changes.all_changed[:10]:
                print(f"     - {f}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    # Test 5: Test with different base (last commit)
    print("\n5. Getting changed files compared to HEAD~1...")
    try:
        changes = git_manager.get_changed_files(base='HEAD~1')
        print(f"   Files changed in last commit: {len(changes.all_changed)}")

        if changes.all_changed:
            print(f"\n   Files that changed in last commit:")
            for f in changes.all_changed[:10]:
                print(f"     - {f}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    print("\n" + "=" * 50)
    print("All tests passed! ✓")
    return True

if __name__ == '__main__':
    success = test_git_integration()
    sys.exit(0 if success else 1)
