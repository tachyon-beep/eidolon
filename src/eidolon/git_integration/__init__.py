"""Git integration for detecting changed files in incremental analysis."""

import subprocess
from pathlib import Path
from typing import List, Set, Optional, Dict
from dataclasses import dataclass


@dataclass
class GitChanges:
    """Represents git changes for incremental analysis"""
    modified: List[str]  # Modified files
    added: List[str]  # Added files
    deleted: List[str]  # Deleted files
    renamed: Dict[str, str]  # Old path -> new path mapping
    all_changed: List[str]  # Combined modified + added (for analysis)


class GitManager:
    """Manages git operations for incremental analysis"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)

    def is_git_repo(self) -> bool:
        """Check if the path is a git repository"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_changed_files(
        self,
        base: Optional[str] = None,
        file_extensions: Optional[Set[str]] = None
    ) -> GitChanges:
        """
        Get changed files compared to a base reference.

        Args:
            base: Base reference (branch, commit, tag). Defaults to 'HEAD' (working directory changes)
            file_extensions: Only include files with these extensions (e.g., {'.py'})

        Returns:
            GitChanges object with categorized changes
        """
        if not self.is_git_repo():
            raise ValueError(f"{self.repo_path} is not a git repository")

        # Default to comparing working directory against HEAD
        if base is None:
            base = 'HEAD'

        modified = []
        added = []
        deleted = []
        renamed = {}

        try:
            # Get status of files compared to base
            result = subprocess.run(
                ['git', 'diff', '--name-status', base],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise RuntimeError(f"Git diff failed: {result.stderr}")

            # Parse git diff output
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('\t')
                if len(parts) < 2:
                    continue

                status = parts[0]
                file_path = parts[1]

                # Filter by extension if specified
                if file_extensions:
                    if not any(file_path.endswith(ext) for ext in file_extensions):
                        continue

                if status == 'M':  # Modified
                    modified.append(file_path)
                elif status == 'A':  # Added
                    added.append(file_path)
                elif status == 'D':  # Deleted
                    deleted.append(file_path)
                elif status.startswith('R'):  # Renamed
                    if len(parts) >= 3:
                        old_path = parts[1]
                        new_path = parts[2]
                        renamed[old_path] = new_path
                        modified.append(new_path)  # Treat renamed as modified

            # Also check for untracked files (not in git yet)
            untracked_result = subprocess.run(
                ['git', 'ls-files', '--others', '--exclude-standard'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            for line in untracked_result.stdout.strip().split('\n'):
                if not line:
                    continue

                # Filter by extension if specified
                if file_extensions:
                    if not any(line.endswith(ext) for ext in file_extensions):
                        continue

                added.append(line)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Git operation timed out")
        except Exception as e:
            raise RuntimeError(f"Git operation failed: {str(e)}")

        # Combine modified and added for analysis
        all_changed = modified + added

        return GitChanges(
            modified=modified,
            added=added,
            deleted=deleted,
            renamed=renamed,
            all_changed=all_changed
        )

    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def get_current_branch(self) -> Optional[str]:
        """Get current branch name"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                return branch if branch != 'HEAD' else None
        except Exception:
            pass
        return None

    def get_file_last_modified_commit(self, file_path: str) -> Optional[str]:
        """Get the commit hash when a file was last modified"""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H', '--', file_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def get_changed_python_files(self, base: Optional[str] = None) -> GitChanges:
        """Convenience method to get changed Python files only"""
        return self.get_changed_files(base, file_extensions={'.py'})
