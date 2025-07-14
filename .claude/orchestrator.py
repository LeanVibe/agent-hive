# .claude/orchestrator.py
#!/usr/bin/env python3
"""Streamlined orchestrator with maximum autonomy"""


class LeanVibeOrchestrator:
    def __init__(self):
        self.state = IntelligentStateManager()
        self.monitor = SmartContextManager()
        self.confidence = ConfidenceOptimizer()
        self.dashboard = UnifiedDashboard()
        self.xp = SmartXPEnforcer()

    async def run(self):
        """Main loop optimized for autonomy"""

        # Start background monitors
        asyncio.create_task(self.monitor.monitor_and_prevent())
        asyncio.create_task(self.health_monitor())

        while True:
            try:
                # Get next work item intelligently
                work_item = await self.get_next_priority()

                if not work_item:
                    await asyncio.sleep(30)
                    continue

                # Check if we can handle autonomously
                if self.confidence.can_handle_autonomously(work_item):
                    await self.execute_autonomously(work_item)
                else:
                    await self.request_human_guidance(work_item)

                # Learn from execution
                outcome = await self.get_execution_outcome(work_item)
                self.confidence.learn_from_outcome(work_item, outcome)

            except Exception as e:
                await self.smart_error_handling(e)

    async def execute_autonomously(self, work_item):
        """Execute with minimal interruption"""

        # Plan with Gemini
        plan = await self.plan_with_gemini(work_item)

        # Distribute smartly
        distribution = self.smart_distribute(plan)

        # Execute in parallel
        tasks = [
            self.execute_on_agent(agent, tasks) for agent, tasks in distribution.items()
        ]

        # Monitor without blocking
        asyncio.create_task(self.monitor_execution(tasks))

    async def smart_error_handling(self, error):
        """Handle errors without always escalating"""

        # Check if we've seen this before
        if solution := self.find_previous_solution(error):
            await self.apply_solution(solution)
            return

        # Try automatic recovery
        if await self.attempt_auto_recovery(error):
            return

        # Only escalate if truly necessary
        await self.escalate_with_context(error)
