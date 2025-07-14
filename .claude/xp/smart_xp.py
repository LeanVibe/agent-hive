# .claude/xp/smart_xp.py
class SmartXPEnforcer:
    """XP practices with minimal interruption"""

    def __init__(self):
        self.test_generator = AutoTestGenerator()
        self.pair_programmer = GeminiPairProgrammer()

    async def ensure_xp_practices(self, file_path, changes):
        """Enforce XP without blocking progress"""

        # Auto-generate tests if missing
        if not self.has_tests(file_path):
            tests = await self.test_generator.generate(file_path, changes)
            await self.create_test_file(file_path, tests)

        # Gemini pair programming in background
        review_task = asyncio.create_task(self.pair_programmer.review_async(changes))

        # Don't block on review unless critical
        if self.is_critical_change(changes):
            review = await review_task
            if review.has_critical_issues():
                return self.request_human_review(review)

        return True  # Continue working
