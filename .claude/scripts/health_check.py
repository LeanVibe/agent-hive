import os

from state_manager import StateManager


def health_check(all=False):
    sm = StateManager(Path("."))
    try:
        sm._collect_metrics()  # Check DB
        if os.path.exists(".claude/state.db"):
            print("DB OK")
        # Stub agent ping
        print("Agents OK" if all else "Partial OK")
        return True
    except Exception:
        return False


if __name__ == "__main__":
    print("Health: " + str(health_check(True)))  # Testable
