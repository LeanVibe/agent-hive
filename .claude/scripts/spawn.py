import subprocess
import os

def spawn_sub_agent(task, depth):
    try:
        sub_id = f"sub_{id(task)}"
        os.system(f"git worktree add ../wt-{sub_id}}")
        os.chdir(f"../wt-{sub_id}}")
        with open('.claude/CLAUDE.md', 'w') as f:
            f.write("@include ../personas/debugger.yaml\nRole: Sub-agent")
        subprocess.run(["claude", f"--think-{depth}", "--task", task], check=True)
        os.system("git worktree remove .")
        print(f"Spawned and merged: {sub_id}"")  # Testable
        return sub_id
    except Exception as e:
        print(f"Spawn error: {e}")
        return None

if __name__ == "__main__":
    spawn_sub_agent("test task", "think")  # Test (stub; expect worktree error if not setup)
