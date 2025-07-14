import json

from state_manager import StateManager


class TaskDistributor:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def distribute(self, tasks, consult_gemini=True):
        agents = json.load(open(".claude/settings.yaml"))["agents"]
        distribution = {}
        for task in tasks:
            complexity = self._estimate_complexity(task)
            depth = "ultrathink" if complexity > 10 else "think"
            best_agent = self._find_best_agent(task, agents)
            if complexity > 15:
                sub_id = spawn_sub_agent(task, depth)  # Assumes spawn imported
                distribution[best_agent] = [task["id"], sub_id]
            else:
                distribution[best_agent] = [task["id"]]
            if consult_gemini:
                prompt = f"Review distribution: {json.dumps(distribution)}. Cite metrics. Confidence?"
                # Stub: Assume Gemini call; for test: print
                print(prompt)
        for agent, task_ids in distribution.items():
            for tid in task_ids:
                self.state_manager.db.execute(
                    "INSERT OR REPLACE INTO tasks VALUES (?, ?, 'assigned', 0.8)",
                    (tid, agent),
                )
                self.state_manager.db.commit()
        print(f"Distributed: {distribution}")  # Testable output
        return distribution

    def _estimate_complexity(self, task):
        return len(task.get("description", "")) / 100 + len(
            task.get("dependencies", [])
        )

    def _find_best_agent(self, task, agents):
        return max(
            agents,
            key=lambda a: len(
                set(task.get("capabilities", [])) & set(agents[a]["capabilities"])
            ),
        )


if __name__ == "__main__":
    # Test stub
    sm = StateManager(Path("."))
    td = TaskDistributor(sm)
    tasks = [{"id": "1", "description": "test", "capabilities": ["python"]}]
    td.distribute(tasks)
