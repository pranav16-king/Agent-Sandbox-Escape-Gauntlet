import os
import threading
from pathlib import Path
from typing import Any, Optional

class WorkspaceManager:
    """
    Manages the active project workspace boundary.
    Guarantees that autonomous coding agents can only inspect, read, write,
    and execute files within the explicitly selected project directory.
    """
    def __init__(self, initial_path: Optional[Path] = None):
        self._lock = threading.Lock()
        # Default to the active repository root
        self._current_path: Path = (initial_path or Path.cwd()).resolve()

    @property
    def current_path(self) -> Path:
        with self._lock:
            return self._current_path

    def set_workspace(self, new_path_str: str) -> dict[str, Any]:
        """
        Sets the active project workspace to a user-selected folder.
        Validates that the folder exists and is a directory.
        """
        clean_str = new_path_str.strip()
        if not clean_str:
            raise ValueError("Workspace path cannot be empty.")

        target = Path(clean_str).resolve()
        if not target.exists():
            raise ValueError(f"Directory does not exist: {clean_str}")
        if not target.is_dir():
            raise ValueError(f"Path is not a directory: {clean_str}")

        with self._lock:
            self._current_path = target

        return self.get_workspace_info()

    def get_workspace_info(self) -> dict[str, Any]:
        """
        Returns structured metadata for the active project workspace,
        including folder name, top-level file manifest, and file count.
        """
        with self._lock:
            root = self._current_path

        is_valid = root.exists() and root.is_dir()
        if not is_valid:
            return {
                "path": root.as_posix(),
                "name": root.name or "workspace",
                "is_valid": False,
                "file_count": 0,
                "files": [],
                "allowed_boundary": root.as_posix()
            }

        ignored_names = {
            ".git", "node_modules", "__pycache__", ".venv", "venv", 
            "dist", "build", ".pytest_cache", ".next"
        }

        top_files: list[dict[str, Any]] = []
        total_count = 0

        try:
            for item in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if item.name in ignored_names or item.name.startswith("."):
                    continue
                
                is_directory = item.is_dir()
                size_bytes = 0
                if not is_directory:
                    try:
                        size_bytes = item.stat().st_size
                    except Exception:
                        pass

                top_files.append({
                    "name": item.name,
                    "type": "directory" if is_directory else "file",
                    "path": item.as_posix(),
                    "size_bytes": size_bytes
                })
                total_count += 1
        except Exception:
            pass

        return {
            "path": root.as_posix(),
            "name": root.name or "workspace",
            "is_valid": True,
            "file_count": len(top_files),
            "files": top_files,
            "allowed_boundary": root.as_posix()
        }

    def resolve_workspace_file(self, raw_path: str) -> Optional[Path]:
        """
        Safely resolves a file path within the active project workspace.
        Returns the resolved Path if inside boundary, or None if it escapes.
        """
        with self._lock:
            root = self._current_path

        clean_path = raw_path.replace("\\", "/").strip()
        
        # Strip leading /workspace or workspace/ virtual mount prefix if present
        if clean_path.startswith("/workspace"):
            clean_path = clean_path[len("/workspace"):].lstrip("/")
        elif clean_path.startswith("workspace/"):
            clean_path = clean_path[len("workspace/"):].lstrip("/")
        
        # If path is absolute and already points inside the project directory
        raw_as_path = Path(clean_path)
        if raw_as_path.is_absolute():
            try:
                resolved = raw_as_path.resolve()
                if resolved.is_relative_to(root):
                    return resolved
                return None
            except (ValueError, Exception):
                return None

        # Relative resolution against root
        try:
            resolved = (root / clean_path).resolve()
            if resolved.is_relative_to(root):
                return resolved
            return None
        except (ValueError, Exception):
            return None

    def is_inside_workspace(self, raw_path: str) -> bool:
        """
        Returns True if the target path is strictly contained inside the active workspace.
        """
        resolved = self.resolve_workspace_file(raw_path)
        return resolved is not None


workspace_manager = WorkspaceManager()
