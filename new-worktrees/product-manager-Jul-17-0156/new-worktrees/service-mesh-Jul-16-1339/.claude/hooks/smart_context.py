# .claude/hooks/smart_context.py
class SmartContextManager:
    """Prevents context overflow before it happens"""

    def __init__(self):
        self.predictor = ContextGrowthPredictor()
        self.summarizer = IntelligentSummarizer()

    async def monitor_and_prevent(self):
        """Run continuously to prevent context issues"""
        while True:
            for agent in self.get_all_agents():
                predicted_overflow_time = self.predictor.predict_overflow(agent)

                if predicted_overflow_time < 30:  # 30 minutes
                    # Proactively summarize before overflow
                    await self.smart_summarize(agent)

                elif predicted_overflow_time < 60:  # 1 hour
                    # Start preparing for checkpoint
                    await self.prepare_checkpoint(agent)

            await asyncio.sleep(300)  # Check every 5 minutes

    async def smart_summarize(self, agent):
        """Summarize with zero information loss"""
        context = await self.get_agent_context(agent)

        # Extract critical elements that must be preserved
        critical = {
            "active_tasks": self.extract_active_tasks(context),
            "decisions_pending": self.extract_pending_decisions(context),
            "errors_unresolved": self.extract_errors(context),
            "architecture": self.extract_architecture(context),
        }

        # Create intelligent summary
        summary = await self.summarizer.summarize_with_preservation(context, critical)

        # Archive full context
        await self.archive_context(agent, context)

        # Update agent with summary
        await self.update_agent_context(agent, summary)
