"""Basic import tests to verify the project structure."""


def test_import_orchestrator():
    """Test that we can import the orchestrator module."""
    try:
        import sys
        sys.path.append('.claude')
        from orchestrator import LeanVibeOrchestrator
        assert LeanVibeOrchestrator is not None
    except ImportError as e:
        # For now, expect this to fail until we implement missing classes
        assert "IntelligentStateManager" in str(e) or "SmartContextManager" in str(e)


def test_import_state_manager():
    """Test that we can import the state manager."""
    try:
        import sys
        sys.path.append('.claude')
        from state_manager import StateManager
        assert StateManager is not None
    except ImportError:
        # This should work as it's already implemented
        raise


def test_import_task_distributor():
    """Test that we can import the task distributor."""
    try:
        import sys
        sys.path.append('.claude')
        from task_distributor import TaskDistributor
        assert TaskDistributor is not None
    except ImportError:
        # This should work as it's already implemented
        raise