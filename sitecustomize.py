"""
Global site customizations to ensure repository imports work reliably under pytest.

This file is automatically imported by Python if present on sys.path.
We ensure the project root and `.claude` shim directory are present early
in sys.path so imports like `config.auth_models` and `.claude/state/state_manager` work.
"""
from pathlib import Path
import sys
import importlib.util
import importlib.abc

project_root = Path(__file__).resolve().parent
claude_dir = project_root / ".claude"

# Prepend to sys.path to take precedence over site-packages with accidental names
root_str = str(project_root)
claude_str = str(claude_dir)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
if claude_dir.exists() and claude_str not in sys.path:
    sys.path.insert(1, claude_str)

# Aggressively ensure local `config` package is used instead of any installed `config` package
try:
    import importlib
    existing_config = sys.modules.get("config")
    if existing_config is not None:
        config_file = getattr(existing_config, "__file__", "")
        if project_root.as_posix() not in (config_file or ""):
            del sys.modules["config"]
    importlib.invalidate_caches()
    # Import local config explicitly to populate sys.modules early
    import config  # type: ignore  # noqa: F401
except Exception:
    # Non-fatal; tests may still set up sys.path
    pass


class _LocalConfigFinder(importlib.abc.MetaPathFinder):
    """Ensure imports of `config` resolve to the repo-local package."""

    def __init__(self, root: Path):
        self.root = root
        self.pkg_dir = self.root / "config"

    def find_spec(self, fullname, path, target=None):
        # Only intercept our intended package
        if fullname == "config":
            init_py = self.pkg_dir / "__init__.py"
            if init_py.exists():
                return importlib.util.spec_from_file_location(
                    "config",
                    str(init_py),
                    submodule_search_locations=[str(self.pkg_dir)],
                )
            return None
        if fullname.startswith("config."):
            rel = fullname.split(".", 1)[1]
            py_path = self.pkg_dir / (rel.replace(".", "/") + ".py")
            if py_path.exists():
                return importlib.util.spec_from_file_location(fullname, str(py_path))
            # Support packages under config/ as needed
            pkg_path = self.pkg_dir / rel.replace(".", "/") / "__init__.py"
            if pkg_path.exists():
                return importlib.util.spec_from_file_location(
                    fullname, str(pkg_path), submodule_search_locations=[str(pkg_path.parent)]
                )
        return None


# Prepend our finder so it wins over site-packages shadowing
sys.meta_path.insert(0, _LocalConfigFinder(project_root))
