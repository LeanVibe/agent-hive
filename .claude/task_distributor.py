import json


class TaskDistributor:
    def __init__(self, state_manager):
        self.state_manager = state_manager

    def distribute(self, tasks, consult_gemini=True):
        # Match capabilities, load from settings.yaml
        agents = json.load(open(".claude/settings.yaml"))["agents"]
        distribution = {}
        for task in tasks:
            complexity = self._estimate_complexity(
                task
            )  # e.g., len(description) + len(deps)
            depth = "ultrathink" if complexity > 10 else "think"  # Adaptive
            best_agent = self._find_best_agent(task, agents)
            if complexity > 15:  # Spawn sub-agent for parallel subtasks
                sub_id = spawn_sub_agent(task, depth)  # From spawn.py
                distribution[best_agent] = [task["id"], sub_id]
            else:
                distribution[best_agent] = [task["id"]]
            # Consult Gemini with evidence-based prompt
            if consult_gemini:
                prompt = f"Review distribution: {json.dumps(distribution)}. Cite metrics. Confidence?"
                # Call Gemini, adjust if <0.8

        # Track in state
        for agent, task_ids in distribution.items():
            for tid in task_ids:
                self.state_manager.db.execute(
                    "INSERT INTO tasks VALUES (?, ?, 'assigned', 0.8)", (tid, agent)
                )

        return distribution

    def _estimate_complexity(self, task):
        return len(task.get("description", "")) / 100 + len(
            task.get("dependencies", [])
        )

    def _find_best_agent(self, task, agents):
        # Simple matching on capabilities
        return max(
            agents,
            key=lambda a: len(
                set(task["capabilities"]) & set(agents[a]["capabilities"])
            ),
        )
