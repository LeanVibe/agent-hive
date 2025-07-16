#!/usr/bin/env python3
"""
PM Auto-Evaluator - Intelligent agent task assignment and escalation
Integrates with Gemini CLI for complex decision making.
"""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PMAutoEvaluator:
    """Automated PM evaluation system with Gemini CLI integration"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pm_agent = "pm-agent-new"
        self.decisions_file = project_root / ".claude/state/pm_decisions.json"
        
        # Decision confidence thresholds
        self.auto_assign_threshold = 0.8
        self.gemini_consult_threshold = 0.6
        self.human_escalation_threshold = 0.4
        
    def evaluate_agent_status(self, agent_name: str, status_content: str) -> Dict:
        """Evaluate agent status and determine next action"""
        
        # Analyze status content for decision making
        analysis = self._analyze_status_content(status_content)
        confidence = analysis['confidence']
        
        decision = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "analysis": analysis,
            "confidence": confidence,
            "action": None,
            "reason": None
        }
        
        if confidence >= self.auto_assign_threshold:
            # High confidence - auto-assign next task
            decision["action"] = "auto_assign"
            decision["reason"] = "High confidence in next task requirements"
            self._auto_assign_task(agent_name, analysis)
            
        elif confidence >= self.gemini_consult_threshold:
            # Medium confidence - consult Gemini CLI
            decision["action"] = "gemini_consult"
            decision["reason"] = "Moderate confidence - consulting Gemini CLI"
            self._consult_gemini_cli(agent_name, analysis)
            
        else:
            # Low confidence - escalate to human
            decision["action"] = "human_escalate"
            decision["reason"] = "Low confidence - requires human judgment"
            self._escalate_to_human(agent_name, analysis)
        
        self._save_decision(decision)
        return decision
    
    def _analyze_status_content(self, content: str) -> Dict:
        """Analyze status content to determine confidence and next steps"""
        
        # Keywords indicating completion
        completion_keywords = [
            "completed", "finished", "done", "ready", "merged", 
            "deployed", "tested", "passing", "successful"
        ]
        
        # Keywords indicating need for next task
        task_request_keywords = [
            "next", "what's next", "ready for", "awaiting", "need task",
            "waiting for", "guidance", "instructions"
        ]
        
        # Keywords indicating issues/blockers
        blocker_keywords = [
            "blocked", "stuck", "error", "failed", "conflict", 
            "issue", "problem", "help needed", "unclear"
        ]
        
        # Keywords indicating in progress
        progress_keywords = [
            "working on", "implementing", "in progress", "developing",
            "testing", "debugging", "updating"
        ]
        
        content_lower = content.lower()
        
        # Score content based on keywords
        completion_score = sum(1 for kw in completion_keywords if kw in content_lower)
        task_request_score = sum(1 for kw in task_request_keywords if kw in content_lower)
        blocker_score = sum(1 for kw in blocker_keywords if kw in content_lower)
        progress_score = sum(1 for kw in progress_keywords if kw in content_lower)
        
        # Determine primary status
        if blocker_score > 0:
            primary_status = "blocked"
            confidence = 0.3  # Low confidence - needs human help
            next_action = "unblock_agent"
        elif completion_score > task_request_score:
            primary_status = "completed"
            confidence = 0.9  # High confidence - assign next task
            next_action = "assign_next_task"
        elif task_request_score > 0:
            primary_status = "ready_for_task"
            confidence = 0.8  # High confidence - agent explicitly asking
            next_action = "assign_next_task"
        elif progress_score > 0:
            primary_status = "in_progress"
            confidence = 0.7  # Medium confidence - let agent continue
            next_action = "monitor"
        else:
            primary_status = "unclear"
            confidence = 0.2  # Very low confidence - need clarification
            next_action = "request_clarification"
        
        return {
            "primary_status": primary_status,
            "confidence": confidence,
            "next_action": next_action,
            "completion_score": completion_score,
            "task_request_score": task_request_score,
            "blocker_score": blocker_score,
            "progress_score": progress_score,
            "keywords_found": {
                "completion": [kw for kw in completion_keywords if kw in content_lower],
                "task_request": [kw for kw in task_request_keywords if kw in content_lower],
                "blocker": [kw for kw in blocker_keywords if kw in content_lower],
                "progress": [kw for kw in progress_keywords if kw in content_lower]
            }
        }
    
    def _auto_assign_task(self, agent_name: str, analysis: Dict):
        """Automatically assign next task based on analysis"""
        
        if analysis["next_action"] == "assign_next_task":
            # Get next task from project plan
            next_task = self._get_next_task_for_agent(agent_name)
            
            if next_task:
                task_message = f"""TASK ASSIGNMENT (AUTO):

Next Task: {next_task['title']}
Priority: {next_task['priority']}
Description: {next_task['description']}

Success Criteria:
{next_task['success_criteria']}

Estimated Time: {next_task['estimated_time']}

Please begin implementation and update status every 2 hours."""
                
                self._send_message_to_agent(agent_name, task_message)
                logger.info(f"✅ Auto-assigned task to {agent_name}: {next_task['title']}")
            else:
                # No more tasks - mark agent as complete
                completion_message = """SPRINT COMPLETION:

✅ All assigned tasks completed successfully!

Please:
1. Final commit and push all changes
2. Run final quality gates
3. Update documentation if needed
4. Report completion status

Great work on Sprint completion! 🎉"""
                
                self._send_message_to_agent(agent_name, completion_message)
                logger.info(f"🎉 Agent {agent_name} sprint completed")
        
        elif analysis["next_action"] == "monitor":
            # Agent working - send encouragement
            monitor_message = """PROGRESS MONITORING:

Good progress! Continue with current task.

Remember to:
- Update status every 2 hours  
- Run tests before commits
- Ask for help if blocked

Keep up the excellent work! 👍"""
            
            self._send_message_to_agent(agent_name, monitor_message)
    
    def _consult_gemini_cli(self, agent_name: str, analysis: Dict):
        """Consult Gemini CLI for complex decisions"""
        
        gemini_prompt = f"""Agent Status Evaluation Request:

Agent: {agent_name}
Status Analysis: {json.dumps(analysis, indent=2)}

Please evaluate and recommend:
1. Should agent continue current task or get new assignment?
2. What specific next task or guidance should be provided?
3. Any risks or blockers to address?
4. Confidence level in recommendation (0.0-1.0)?

Provide structured recommendation with reasoning."""
        
        try:
            # Call Gemini CLI (assuming it's available)
            gemini_result = subprocess.run([
                "gemini", "evaluate", "--prompt", gemini_prompt
            ], capture_output=True, text=True, timeout=60)
            
            if gemini_result.returncode == 0:
                gemini_response = gemini_result.stdout
                self._process_gemini_recommendation(agent_name, gemini_response, analysis)
            else:
                logger.warning(f"⚠️ Gemini CLI failed, escalating to human for {agent_name}")
                self._escalate_to_human(agent_name, analysis)
                
        except Exception as e:
            logger.error(f"❌ Gemini CLI error: {e}")
            logger.info(f"📞 Escalating {agent_name} to human due to Gemini failure")
            self._escalate_to_human(agent_name, analysis)
    
    def _process_gemini_recommendation(self, agent_name: str, gemini_response: str, analysis: Dict):
        """Process and act on Gemini CLI recommendation"""
        
        # Parse Gemini recommendation (simplified - would need proper parsing)
        if "continue current task" in gemini_response.lower():
            self._auto_assign_task(agent_name, {"next_action": "monitor"})
        elif "assign new task" in gemini_response.lower():
            self._auto_assign_task(agent_name, {"next_action": "assign_next_task"})
        else:
            # Complex recommendation - escalate to human with Gemini context
            self._escalate_to_human(agent_name, analysis, gemini_context=gemini_response)
    
    def _escalate_to_human(self, agent_name: str, analysis: Dict, gemini_context: str = None):
        """Escalate decision to human with full context"""
        
        context_info = f"""HUMAN ESCALATION REQUIRED:

Agent: {agent_name}
Status Analysis: {json.dumps(analysis, indent=2)}

Confidence Level: {analysis['confidence']:.2f} (below threshold)
Primary Status: {analysis['primary_status']}
Recommended Action: {analysis['next_action']}

{f"Gemini CLI Context: {gemini_context}" if gemini_context else ""}

HUMAN ACTION NEEDED:
Please review agent status and provide guidance on next steps.
This decision requires human judgment due to complexity or ambiguity."""
        
        # Log escalation (in production, this would notify via Slack/email)
        logger.warning(f"🚨 HUMAN ESCALATION: {agent_name}")
        
        # Send status to PM agent for human review
        pm_message = f"""ESCALATION TO HUMAN REQUIRED:

{context_info}

Please coordinate with human team lead for decision on {agent_name}'s next steps."""
        
        self._send_message_to_agent(self.pm_agent, pm_message)
    
    def _get_next_task_for_agent(self, agent_name: str) -> Optional[Dict]:
        """Get next task for agent from project plan"""
        
        # This would integrate with actual project planning system
        # For now, return mock tasks based on agent type
        
        task_map = {
            "integration-specialist": {
                "title": "Week 2: Security Hardening - JWT Authentication",
                "priority": "high", 
                "description": "Implement JWT authentication system with secure token handling",
                "success_criteria": "JWT auth working, tests passing, security audit clean",
                "estimated_time": "6-8 hours"
            },
            "service-mesh": {
                "title": "Week 2: Distributed Rate Limiting",
                "priority": "high",
                "description": "Implement distributed rate limiting across service mesh",
                "success_criteria": "Rate limiting active, performance benchmarks met",
                "estimated_time": "4-6 hours"
            },
            "frontend": {
                "title": "Week 2: Security Dashboard UI",
                "priority": "medium",
                "description": "Create security monitoring dashboard with real-time alerts",
                "success_criteria": "Dashboard functional, real-time updates working",
                "estimated_time": "6-8 hours"
            }
        }
        
        # Get agent type from name
        for agent_type in task_map:
            if agent_type in agent_name:
                return task_map[agent_type]
        
        return None
    
    def _send_message_to_agent(self, agent_name: str, message: str):
        """Send message to specific agent"""
        try:
            cmd = [
                "python", "scripts/fixed_agent_communication.py",
                "--agent", agent_name,
                "--message", message
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Message sent to {agent_name}")
            else:
                logger.error(f"❌ Failed to send message to {agent_name}: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Exception sending message to {agent_name}: {e}")
    
    def _save_decision(self, decision: Dict):
        """Save PM decision to tracking file"""
        decisions = []
        if self.decisions_file.exists():
            with open(self.decisions_file, 'r') as f:
                decisions = json.load(f)
        
        decisions.append(decision)
        
        # Keep only last 100 decisions
        decisions = decisions[-100:]
        
        self.decisions_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.decisions_file, 'w') as f:
            json.dump(decisions, f, indent=2)

def main():
    """CLI interface for PM auto-evaluation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PM Auto-Evaluator")
    parser.add_argument("--agent", required=True, help="Agent name to evaluate")
    parser.add_argument("--status", required=True, help="Agent status content")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent.parent
    evaluator = PMAutoEvaluator(project_root)
    
    decision = evaluator.evaluate_agent_status(args.agent, args.status)
    
    print(f"Decision: {decision['action']}")
    print(f"Confidence: {decision['confidence']:.2f}")
    print(f"Reason: {decision['reason']}")

if __name__ == "__main__":
    main()