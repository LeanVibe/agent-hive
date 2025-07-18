import json
import sqlite3

import git


def monitor():
    try:
        db = sqlite3.connect(".claude/state.db")
        cursor = db.cursor()
        cursor.execute("SELECT agent, AVG(confidence) FROM tasks GROUP BY agent")
        confidences = cursor.fetchall()
        repo = git.Repo(".")
        recent = repo.git.log("--oneline", "-n", "5")
        # Stub health
        for agent, avg_conf in confidences:
            if avg_conf < 0.8:
                print(f"Redistributing from {agent}")
        output = {"confidences": confidences, "recent": recent}
        print(json.dumps(output))  # Testable CLI output
        return output
    except Exception as e:
        print(f"Monitor error: {e}")
        return None


if __name__ == "__main__":
    monitor()
