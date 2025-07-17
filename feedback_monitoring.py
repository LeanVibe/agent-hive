#!/usr/bin/env python3
"""
Feedback Implementation Monitoring System

Tracks the progress of review agents and coordinates handoff to implementation agents.
Monitors GitHub issues for completion signals and triggers implementation phases.
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import subprocess
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('feedback_monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Status of review/implementation agents"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ERROR = "error"

class FeedbackPhase(Enum):
    """Phase of feedback implementation workflow"""
    REVIEW = "review"
    IMPLEMENTATION = "implementation"
    VALIDATION = "validation"
    COMPLETE = "complete"

@dataclass
class Agent:
    """Represents a review or implementation agent"""
    issue_number: int
    agent_type: str  # 'review' or 'implementation'
    focus_area: str
    status: AgentStatus
    phase: FeedbackPhase
    last_update: datetime
    progress_percentage: int = 0
    feedback_items: List[str] = None

    def __post_init__(self):
        if self.feedback_items is None:
            self.feedback_items = []

@dataclass
class AgentPair:
    """Represents a review-implementation agent pair"""
    review_agent: Agent
    implementation_agent: Agent
    focus_area: str
    handoff_complete: bool = False
    handoff_timestamp: Optional[datetime] = None

class FeedbackMonitor:
    """Monitors feedback implementation workflow"""

    def __init__(self):
        self.agent_pairs: List[AgentPair] = []
        self.monitoring_active = False
        self.check_interval = 300  # 5 minutes
        self.escalation_threshold = timedelta(hours=2)
        self.timeout_threshold = timedelta(hours=8)

        # Initialize agent pairs
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize agent pairs with current GitHub issues"""
        pairs_config = [
            {
                'review_issue': 12,
                'implementation_issue': 17,
                'focus_area': 'Documentation',
                'review_type': 'Documentation Review',
                'implementation_type': 'Documentation Implementation'
            },
            {
                'review_issue': 13,
                'implementation_issue': 18,
                'focus_area': 'Tutorial',
                'review_type': 'Tutorial Review',
                'implementation_type': 'Tutorial Implementation'
            },
            {
                'review_issue': 14,
                'implementation_issue': 19,
                'focus_area': 'Quality',
                'review_type': 'Quality Assurance',
                'implementation_type': 'Quality Implementation'
            },
            {
                'review_issue': 15,
                'implementation_issue': 20,
                'focus_area': 'Architecture',
                'review_type': 'Architecture Review',
                'implementation_type': 'Integration Implementation'
            }
        ]

        for config in pairs_config:
            review_agent = Agent(
                issue_number=config['review_issue'],
                agent_type='review',
                focus_area=config['focus_area'],
                status=AgentStatus.IN_PROGRESS,
                phase=FeedbackPhase.REVIEW,
                last_update=datetime.now()
            )

            implementation_agent = Agent(
                issue_number=config['implementation_issue'],
                agent_type='implementation',
                focus_area=config['focus_area'],
                status=AgentStatus.PENDING,
                phase=FeedbackPhase.REVIEW,
                last_update=datetime.now()
            )

            pair = AgentPair(
                review_agent=review_agent,
                implementation_agent=implementation_agent,
                focus_area=config['focus_area']
            )

            self.agent_pairs.append(pair)

    def _run_github_command(self, command: List[str]) -> Tuple[bool, str]:
        """Run GitHub CLI command and return success status and output"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(command)}")
            return False, "Command timed out"
        except Exception as e:
            logger.error(f"Command failed: {' '.join(command)}, Error: {e}")
            return False, str(e)

    def _get_issue_comments(self, issue_number: int) -> List[str]:
        """Get comments from a GitHub issue"""
        success, output = self._run_github_command([
            'gh', 'issue', 'view', str(issue_number), '--json', 'comments'
        ])

        if not success:
            logger.error(f"Failed to get comments for issue {issue_number}")
            return []

        try:
            issue_data = json.loads(output)
            return [comment['body'] for comment in issue_data.get('comments', [])]
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response for issue {issue_number}")
            return []

    def _check_completion_signals(self, comments: List[str]) -> Dict[str, bool]:
        """Check for completion signals in issue comments"""
        signals = {
            'review_complete': False,
            'implementation_ready': False,
            'changes_implemented': False,
            'validation_needed': False,
            'approved': False,
            'merge_ready': False
        }

        for comment in comments:
            comment_lower = comment.lower()
            if '@review-complete' in comment_lower:
                signals['review_complete'] = True
            if '@implementation-ready' in comment_lower:
                signals['implementation_ready'] = True
            if '@changes-implemented' in comment_lower:
                signals['changes_implemented'] = True
            if '@validation-needed' in comment_lower:
                signals['validation_needed'] = True
            if '@approved' in comment_lower:
                signals['approved'] = True
            if '@merge-ready' in comment_lower:
                signals['merge_ready'] = True

        return signals

    def _extract_feedback_items(self, comments: List[str]) -> List[str]:
        """Extract feedback items from issue comments"""
        feedback_items = []

        for comment in comments:
            # Look for feedback patterns
            lines = comment.split('\n')
            for line in lines:
                line = line.strip()
                # Look for common feedback patterns
                if (line.startswith('- [ ]') or
                    line.startswith('- [x]') or
                    line.startswith('* [ ]') or
                    line.startswith('* [x]') or
                    'TODO:' in line or
                    'FIXME:' in line or
                    'Issue:' in line):
                    feedback_items.append(line)

        return feedback_items

    def _update_agent_status(self, agent: Agent):
        """Update agent status based on GitHub issue"""
        comments = self._get_issue_comments(agent.issue_number)
        signals = self._check_completion_signals(comments)

        # Update feedback items
        agent.feedback_items = self._extract_feedback_items(comments)

        # Update status based on signals and agent type
        if agent.agent_type == 'review':
            if signals['review_complete']:
                agent.status = AgentStatus.COMPLETED
                agent.phase = FeedbackPhase.IMPLEMENTATION
            elif signals['implementation_ready']:
                agent.status = AgentStatus.IN_PROGRESS
                agent.phase = FeedbackPhase.REVIEW
        else:  # implementation agent
            if signals['merge_ready']:
                agent.status = AgentStatus.COMPLETED
                agent.phase = FeedbackPhase.COMPLETE
            elif signals['approved']:
                agent.status = AgentStatus.COMPLETED
                agent.phase = FeedbackPhase.VALIDATION
            elif signals['validation_needed']:
                agent.status = AgentStatus.COMPLETED
                agent.phase = FeedbackPhase.VALIDATION
            elif signals['changes_implemented']:
                agent.status = AgentStatus.COMPLETED
                agent.phase = FeedbackPhase.IMPLEMENTATION
            elif signals['implementation_ready']:
                agent.status = AgentStatus.IN_PROGRESS
                agent.phase = FeedbackPhase.IMPLEMENTATION

        # Update progress percentage based on feedback items
        if agent.feedback_items:
            completed_items = sum(1 for item in agent.feedback_items if '[x]' in item)
            total_items = len(agent.feedback_items)
            agent.progress_percentage = int((completed_items / total_items) * 100) if total_items > 0 else 0

        agent.last_update = datetime.now()

    def _trigger_handoff(self, pair: AgentPair):
        """Trigger handoff from review to implementation agent"""
        if pair.handoff_complete:
            return

        # Post handoff signal to implementation agent issue
        handoff_message = f"""
🔄 **HANDOFF SIGNAL: Review Complete**

The {pair.review_agent.focus_area} Review Agent (#{pair.review_agent.issue_number}) has completed their analysis.

**Feedback Items**: {len(pair.review_agent.feedback_items)} items identified
**Implementation Agent**: Ready to begin implementation phase

**Next Steps**:
1. Review feedback items from issue #{pair.review_agent.issue_number}
2. Prioritize implementation tasks
3. Begin implementing changes
4. Provide status updates every 2 hours

**Coordination**:
- Reference issue #{pair.review_agent.issue_number} for detailed feedback
- Use coordination signals for status updates
- Escalate complex issues to @human-lead

@implementation-agent-ready
"""

        success, _ = self._run_github_command([
            'gh', 'issue', 'comment', str(pair.implementation_agent.issue_number),
            '--body', handoff_message
        ])

        if success:
            pair.handoff_complete = True
            pair.handoff_timestamp = datetime.now()
            logger.info(f"Handoff triggered for {pair.focus_area} agents")
        else:
            logger.error(f"Failed to trigger handoff for {pair.focus_area} agents")

    def _check_escalation_needed(self, agent: Agent) -> bool:
        """Check if agent needs escalation due to timeout or blocked status"""
        now = datetime.now()
        time_since_update = now - agent.last_update

        # Check for timeout
        if time_since_update > self.timeout_threshold:
            return True

        # Check for blocked status
        if agent.status == AgentStatus.BLOCKED:
            return True

        # Check for no progress
        if (time_since_update > self.escalation_threshold and
            agent.progress_percentage < 25):
            return True

        return False

    def _escalate_agent(self, agent: Agent):
        """Escalate agent to human intervention"""
        escalation_message = f"""
🚨 **ESCALATION REQUIRED**

Agent: {agent.focus_area} {agent.agent_type.title()} Agent
Status: {agent.status.value}
Last Update: {agent.last_update.strftime('%Y-%m-%d %H:%M:%S')}
Progress: {agent.progress_percentage}%

**Escalation Reasons**:
- Time since last update: {datetime.now() - agent.last_update}
- Current status: {agent.status.value}
- Progress level: {agent.progress_percentage}%

**Required Actions**:
1. Review agent status and blockers
2. Provide guidance or technical assistance
3. Adjust timeline expectations if needed
4. Consider reassigning or additional resources

@human-lead intervention required
"""

        success, _ = self._run_github_command([
            'gh', 'issue', 'comment', str(agent.issue_number),
            '--body', escalation_message
        ])

        if success:
            logger.warning(f"Escalation triggered for {agent.focus_area} {agent.agent_type} agent")
        else:
            logger.error(f"Failed to escalate {agent.focus_area} {agent.agent_type} agent")

    def monitor_cycle(self):
        """Run one monitoring cycle"""
        logger.info("Starting monitoring cycle")

        for pair in self.agent_pairs:
            # Update agent statuses
            self._update_agent_status(pair.review_agent)
            self._update_agent_status(pair.implementation_agent)

            # Check for handoff trigger
            if (pair.review_agent.status == AgentStatus.COMPLETED and
                pair.review_agent.phase == FeedbackPhase.IMPLEMENTATION and
                not pair.handoff_complete):
                self._trigger_handoff(pair)

            # Check for escalation needs
            if self._check_escalation_needed(pair.review_agent):
                self._escalate_agent(pair.review_agent)

            if self._check_escalation_needed(pair.implementation_agent):
                self._escalate_agent(pair.implementation_agent)

        # Log overall progress
        self._log_progress_summary()

    def _log_progress_summary(self):
        """Log overall progress summary"""
        total_agents = len(self.agent_pairs) * 2
        completed_agents = sum(1 for pair in self.agent_pairs
                             for agent in [pair.review_agent, pair.implementation_agent]
                             if agent.status == AgentStatus.COMPLETED)

        overall_progress = (completed_agents / total_agents) * 100

        logger.info(f"Overall Progress: {overall_progress:.1f}% ({completed_agents}/{total_agents} agents completed)")

        for pair in self.agent_pairs:
            logger.info(f"{pair.focus_area}: Review {pair.review_agent.status.value} ({pair.review_agent.progress_percentage}%), "
                       f"Implementation {pair.implementation_agent.status.value} ({pair.implementation_agent.progress_percentage}%)")

    def start_monitoring(self):
        """Start the monitoring loop"""
        self.monitoring_active = True
        logger.info("Feedback monitoring started")

        try:
            while self.monitoring_active:
                self.monitor_cycle()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
        finally:
            self.monitoring_active = False

    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.monitoring_active = False
        logger.info("Feedback monitoring stopped")

    def get_status_report(self) -> Dict:
        """Get current status report"""
        # Update all agents first
        for pair in self.agent_pairs:
            self._update_agent_status(pair.review_agent)
            self._update_agent_status(pair.implementation_agent)

        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_progress': 0,
            'agent_pairs': []
        }

        total_agents = len(self.agent_pairs) * 2
        completed_agents = 0

        for pair in self.agent_pairs:
            pair_data = {
                'focus_area': pair.focus_area,
                'handoff_complete': pair.handoff_complete,
                'handoff_timestamp': pair.handoff_timestamp.isoformat() if pair.handoff_timestamp else None,
                'review_agent': asdict(pair.review_agent),
                'implementation_agent': asdict(pair.implementation_agent)
            }

            # Convert datetime objects to strings
            pair_data['review_agent']['last_update'] = pair.review_agent.last_update.isoformat()
            pair_data['implementation_agent']['last_update'] = pair.implementation_agent.last_update.isoformat()

            # Convert enum values to strings
            pair_data['review_agent']['status'] = pair.review_agent.status.value
            pair_data['review_agent']['phase'] = pair.review_agent.phase.value
            pair_data['implementation_agent']['status'] = pair.implementation_agent.status.value
            pair_data['implementation_agent']['phase'] = pair.implementation_agent.phase.value

            if pair.review_agent.status == AgentStatus.COMPLETED:
                completed_agents += 1
            if pair.implementation_agent.status == AgentStatus.COMPLETED:
                completed_agents += 1

            report['agent_pairs'].append(pair_data)

        report['overall_progress'] = (completed_agents / total_agents) * 100

        return report

def main():
    """Main monitoring function"""
    monitor = FeedbackMonitor()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'start':
            monitor.start_monitoring()
        elif command == 'status':
            report = monitor.get_status_report()
            print(json.dumps(report, indent=2))
        elif command == 'cycle':
            monitor.monitor_cycle()
        else:
            print("Usage: python feedback_monitoring.py [start|status|cycle]")
    else:
        print("Usage: python feedback_monitoring.py [start|status|cycle]")

if __name__ == "__main__":
    main()
