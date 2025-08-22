"""
Path configuration for academicOps
Provides environment-based path resolution for multi-machine deployment
"""
import os
from pathlib import Path
from typing import Optional

class AcademicOpsPaths:
    """Centralized path management for academicOps system"""
    
    def __init__(self):
        # Detect the bot root based on this file's location
        config_dir = Path(__file__).parent
        self.bot_root = config_dir.parent
        
        # Get parent directory from environment or use default
        env_root = os.environ.get('ACADEMIC_OPS_ROOT')
        if env_root:
            self.root = Path(env_root)
        else:
            # Default: parent directory of the bot repository
            self.root = self.bot_root.parent
        
        # Define standard paths
        self.data = self.root / 'data'
        self.docs = self.root / 'docs'
        self.projects = self.root / 'projects'
        self.scripts = self.bot_root / 'scripts'
        self.bot_docs = self.bot_root / 'docs'
        
        # Task-specific paths
        self.tasks = self.data / 'tasks'
        self.task_inbox = self.tasks / 'inbox'
        self.goals = self.data / 'goals'
        self.project_files = self.data / 'projects'
        self.views = self.data / 'views'
        
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate that required directories exist
        Returns: (success: bool, missing_dirs: list[str])
        """
        missing = []
        required_paths = [
            ('root', self.root),
            ('bot_root', self.bot_root),
            ('data', self.data),
        ]
        
        for name, path in required_paths:
            if not path.exists():
                missing.append(f"{name}: {path}")
        
        return len(missing) == 0, missing
    
    def ensure_directories(self):
        """Create required directories if they don't exist"""
        directories = [
            self.data,
            self.tasks,
            self.task_inbox,
            self.goals,
            self.project_files,
            self.views,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_relative_path(self, absolute_path: Path) -> Optional[Path]:
        """
        Convert an absolute path to a relative path from the root
        Returns None if the path is not under the root
        """
        try:
            return absolute_path.relative_to(self.root)
        except ValueError:
            return None
    
    def resolve_path(self, path_str: str) -> Path:
        """
        Resolve a path string, handling both absolute and relative paths
        Relative paths are resolved relative to the root directory
        """
        path = Path(path_str)
        if path.is_absolute():
            return path
        return self.root / path
    
    def __str__(self) -> str:
        """Print current configuration"""
        return f"""Academic Ops Path Configuration:
  ACADEMIC_OPS_ROOT: {self.root}
  ACADEMIC_OPS_BOT: {self.bot_root}
  ACADEMIC_OPS_DATA: {self.data}
  ACADEMIC_OPS_DOCS: {self.docs}
  ACADEMIC_OPS_PROJECTS: {self.projects}
  ACADEMIC_OPS_SCRIPTS: {self.scripts}"""

# Create a singleton instance
paths = AcademicOpsPaths()

# Export commonly used paths for convenience
ROOT = paths.root
BOT_ROOT = paths.bot_root
DATA = paths.data
DOCS = paths.docs
PROJECTS = paths.projects
SCRIPTS = paths.scripts