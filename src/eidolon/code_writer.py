"""
Code Writer Module

Handles writing generated code to files, creating backups,
and managing file operations safely.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import shutil
import os
from datetime import datetime, timezone

from eidolon.logging_config import get_logger

logger = get_logger(__name__)


class CodeWriter:
    """
    Manages safe writing of generated code to files

    Features:
    - Creates backups before modifying files
    - Atomic writes (temp file + rename)
    - Rollback support
    - Directory creation
    """

    def __init__(self, project_path: str, backup_dir: Optional[str] = None):
        self.project_path = Path(project_path)
        self.backup_dir = Path(backup_dir) if backup_dir else self.project_path / ".monad_backups"
        self.session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Track all changes in this session
        self.changes: List[Dict[str, Any]] = []

    def write_file(
        self,
        file_path: str,
        content: str,
        create_backup: bool = True
    ) -> Dict[str, Any]:
        """
        Write content to a file

        Args:
            file_path: Relative path from project root (e.g., "services/auth_service.py")
            content: Code content to write
            create_backup: Whether to create backup if file exists

        Returns:
            Dict with operation details
        """
        full_path = self.project_path / file_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup if file exists
        backup_path = None
        if create_backup and full_path.exists():
            backup_path = self._create_backup(full_path)

        # Write to temp file first (atomic write)
        temp_path = full_path.with_suffix(full_path.suffix + ".tmp")
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Rename to final location (atomic on POSIX systems)
            temp_path.replace(full_path)

            # Track change
            change_record = {
                "file_path": file_path,
                "full_path": str(full_path),
                "backup_path": str(backup_path) if backup_path else None,
                "operation": "modify" if backup_path else "create",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.changes.append(change_record)

            logger.info(
                "file_written",
                file=file_path,
                operation=change_record["operation"],
                backup=bool(backup_path)
            )

            return {
                "success": True,
                "file_path": file_path,
                "operation": change_record["operation"],
                "backup": backup_path
            }

        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()

            logger.error("file_write_failed", file=file_path, error=str(e))
            raise

    def write_class(
        self,
        module_path: str,
        class_name: str,
        class_code: str,
        existing_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write or update a class in a module

        Args:
            module_path: Path to module file (e.g., "services/auth_service.py")
            class_name: Name of the class
            class_code: Complete class code
            existing_content: Existing file content (if modifying)

        Returns:
            Dict with operation details
        """
        full_path = self.project_path / module_path

        if existing_content:
            # Insert class into existing content
            # For now, append to end (in production, would use AST manipulation)
            new_content = existing_content.rstrip() + "\n\n\n" + class_code + "\n"
        else:
            # New file - add standard header
            new_content = '"""\n'
            new_content += f"Module: {Path(module_path).name}\n"
            new_content += '"""\n\n'
            new_content += class_code + "\n"

        return self.write_file(module_path, new_content)

    def write_function(
        self,
        module_path: str,
        function_code: str,
        existing_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write or update a standalone function in a module

        Args:
            module_path: Path to module file
            function_code: Complete function code
            existing_content: Existing file content (if modifying)

        Returns:
            Dict with operation details
        """
        if existing_content:
            new_content = existing_content.rstrip() + "\n\n\n" + function_code + "\n"
        else:
            new_content = '"""\n'
            new_content += f"Module: {Path(module_path).name}\n"
            new_content += '"""\n\n'
            new_content += function_code + "\n"

        return self.write_file(module_path, new_content)

    def _create_backup(self, file_path: Path) -> Path:
        """Create backup of a file"""
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Create session directory
        session_dir = self.backup_dir / self.session_id
        session_dir.mkdir(exist_ok=True)

        # Create backup with relative path structure
        rel_path = file_path.relative_to(self.project_path)
        backup_path = session_dir / rel_path

        # Ensure backup parent directory exists
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(file_path, backup_path)

        logger.info("backup_created", file=str(rel_path), backup=str(backup_path))
        return backup_path

    def rollback(self) -> Dict[str, Any]:
        """
        Rollback all changes made in this session

        Returns:
            Dict with rollback results
        """
        rollback_count = 0
        errors = []

        for change in reversed(self.changes):
            try:
                full_path = Path(change["full_path"])
                backup_path = Path(change["backup_path"]) if change["backup_path"] else None

                if change["operation"] == "create":
                    # Delete created file
                    if full_path.exists():
                        full_path.unlink()
                        logger.info("rollback_delete", file=change["file_path"])
                        rollback_count += 1

                elif change["operation"] == "modify":
                    # Restore from backup
                    if backup_path and backup_path.exists():
                        shutil.copy2(backup_path, full_path)
                        logger.info("rollback_restore", file=change["file_path"])
                        rollback_count += 1

            except Exception as e:
                error_msg = f"Failed to rollback {change['file_path']}: {str(e)}"
                errors.append(error_msg)
                logger.error("rollback_failed", file=change["file_path"], error=str(e))

        return {
            "success": len(errors) == 0,
            "rollback_count": rollback_count,
            "total_changes": len(self.changes),
            "errors": errors
        }

    def get_changes(self) -> List[Dict[str, Any]]:
        """Get list of all changes made in this session"""
        return self.changes.copy()

    def commit_session(self):
        """
        Commit session - clear changes tracking

        Call this after successful implementation to clear the change log.
        Backups remain for manual recovery if needed.
        """
        logger.info(
            "session_committed",
            session_id=self.session_id,
            changes=len(self.changes)
        )
        self.changes.clear()
