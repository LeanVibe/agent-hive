"""Compatibility shim for tests that import state from `.claude`.

This module dynamically loads the real project `state/state_manager.py` and
re-exports its public API so tests that add `.claude` to `sys.path` can still
import `StateManager`, `AgentState`, `TaskState`, and `SystemState` as expected.
"""

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys

_project_root = Path(__file__).resolve().parents[3]
_real_state_path = _project_root / "state" / "state_manager.py"

_spec = spec_from_file_location("_real_state_manager", str(_real_state_path))
if _spec and _spec.loader:  # Load the real module from the project source
    _mod = module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
else:
    raise ImportError(f"Unable to load real state_manager from {_real_state_path}")

# Re-export the expected symbols
StateManager = _mod.StateManager
AgentState = _mod.AgentState
TaskState = _mod.TaskState
SystemState = _mod.SystemState

__all__ = ["StateManager", "AgentState", "TaskState", "SystemState"]
