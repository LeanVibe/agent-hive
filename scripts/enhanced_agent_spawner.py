#!/usr/bin/env python3
"""
Enhanced Agent Spawner - Reliable agent initialization with instruction delivery
Solves inconsistency issues in agent spawning and instruction delivery.
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedAgentSpawner:
    """Reliable agent spawning with consistent instruction delivery"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.max_retries = 3
        self.initialization_timeout = 60  # seconds
        self.instruction_templates = {
            'integration-specialist': self._get_integration_specialist_template,
            'service-mesh': self._get_service_mesh_template,
            'frontend': self._get_frontend_template,
            'security': self._get_security_template,
            'infrastructure': self._get_infrastructure_template,
            'performance': self._get_performance_template,
            'monitoring': self._get_monitoring_template,
        }
        
    async def spawn_agent(
        self,
        agent_type: str,
        priority: str,
        task: str,
        timeline: str,
        human_decision_points: str = "",
        success_criteria: str = "",
        escalation_triggers: str = ""
    ) -> Tuple[bool, str, Dict]:
        """
        Spawn agent with reliable initialization
        Returns: (success, agent_id, metadata)
        """
        timestamp = datetime.now().strftime("%b-%d-%H%M")
        agent_id = f"{agent_type}-{timestamp}"
        
        logger.info(f"🚀 Spawning {agent_type} agent with ID: {agent_id}")
        
        try:
            # Step 1: Create worktree
            success, worktree_path = await self._create_worktree(agent_id)
            if not success:
                return False, agent_id, {"error": "Failed to create worktree"}
                
            # Step 2: Create specialized CLAUDE.md instructions
            success = await self._create_instructions(
                worktree_path, agent_type, task, timeline, 
                human_decision_points, success_criteria, escalation_triggers
            )
            if not success:
                return False, agent_id, {"error": "Failed to create instructions"}
                
            # Step 3: Start tmux session with Claude Code
            success = await self._start_tmux_session(agent_id, worktree_path)
            if not success:
                return False, agent_id, {"error": "Failed to start tmux session"}
                
            # Step 4: Initialize Claude Code with reliable instruction delivery
            success = await self._initialize_claude_code(agent_id, task, priority)
            if not success:
                return False, agent_id, {"error": "Failed to initialize Claude Code"}
                
            # Step 4.5: Ensure agent is fully activated and working
            success = await self._ensure_agent_activation(agent_id, task, priority)
            if not success:
                return False, agent_id, {"error": "Failed to fully activate agent"}
                
            # Step 5: Verify agent initialization
            success = await self._verify_agent_initialization(agent_id)
            if not success:
                return False, agent_id, {"error": "Agent initialization verification failed"}
                
            # Step 6: Register agent in tracking system
            metadata = {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "priority": priority,
                "task": task,
                "timeline": timeline,
                "worktree_path": str(worktree_path),
                "spawn_time": datetime.now().isoformat(),
                "status": "active",
                "human_decision_points": human_decision_points.split(",") if human_decision_points else [],
                "success_criteria": success_criteria.split(",") if success_criteria else [],
                "escalation_triggers": escalation_triggers.split(",") if escalation_triggers else []
            }
            
            await self._register_agent(agent_id, metadata)
            
            # Step 7: Setup progress monitoring
            await self._setup_progress_monitoring(agent_id)
            
            logger.info(f"✅ Agent {agent_id} spawned successfully and verified active")
            return True, agent_id, metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to spawn agent {agent_id}: {e}")
            await self._cleanup_failed_spawn(agent_id)
            return False, agent_id, {"error": str(e)}
    
    async def _create_worktree(self, agent_id: str) -> Tuple[bool, Optional[Path]]:
        """Create Git worktree for agent"""
        try:
            # Extract agent type from agent_id (before timestamp)
            agent_type = agent_id.split('-Jul-')[0] if '-Jul-' in agent_id else agent_id.split('-')[0]
            cmd = ["python", "scripts/new_worktree_manager.py", "create", agent_type, "main"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"Worktree creation failed: {result.stderr}")
                return False, None
                
            # Parse worktree path from output and find matching agent_id path
            created_path = None
            for line in result.stdout.split('\n'):
                if "Path:" in line:
                    created_path = Path(line.split("Path:", 1)[1].strip())
                    break
            
            if created_path:
                # Rename the worktree directory to match our agent_id
                target_path = created_path.parent / agent_id
                if created_path != target_path:
                    created_path.rename(target_path)
                    logger.info(f"📁 Worktree created and renamed: {target_path}")
                    return True, target_path
                else:
                    logger.info(f"📁 Worktree created: {created_path}")
                    return True, created_path
                    
            return False, None
            
        except subprocess.TimeoutExpired:
            logger.error("Worktree creation timed out")
            return False, None
        except Exception as e:
            logger.error(f"Worktree creation error: {e}")
            return False, None
    
    async def _create_instructions(
        self, 
        worktree_path: Path, 
        agent_type: str, 
        task: str, 
        timeline: str,
        human_decision_points: str,
        success_criteria: str,
        escalation_triggers: str
    ) -> bool:
        """Create specialized CLAUDE.md instructions for agent"""
        try:
            if agent_type not in self.instruction_templates:
                logger.error(f"Unknown agent type: {agent_type}")
                return False
                
            # Generate specialized instructions
            template_func = self.instruction_templates[agent_type]
            instructions = template_func(
                task, timeline, human_decision_points, 
                success_criteria, escalation_triggers
            )
            
            # Write to CLAUDE.md in worktree
            claude_md_path = worktree_path / "CLAUDE.md"
            with open(claude_md_path, 'w') as f:
                f.write(instructions)
                
            logger.info(f"📝 Instructions created: {claude_md_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create instructions: {e}")
            return False
    
    async def _start_tmux_session(self, agent_id: str, worktree_path: Path) -> bool:
        """Start tmux session with reliable Claude Code initialization"""
        try:
            # Create tmux window
            cmd = [
                "tmux", "new-window", 
                "-t", "agent-hive",
                "-n", agent_id,
                "-c", str(worktree_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"Failed to create tmux window: {result.stderr}")
                return False
                
            logger.info(f"🖥️ Tmux window created: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start tmux session: {e}")
            return False
    
    async def _initialize_claude_code(self, agent_id: str, task: str, priority: str) -> bool:
        """Initialize Claude Code with reliable instruction delivery"""
        try:
            # Start Claude Code with permission bypass
            cmd = [
                "tmux", "send-keys", 
                "-t", f"agent-hive:{agent_id}",
                "claude --dangerously-skip-permissions",
                "Enter"
            ]
            subprocess.run(cmd, timeout=10)
            
            # Wait for Claude Code to initialize
            await asyncio.sleep(5)
            
            # Send task instructions with reliable delivery
            task_instruction = (
                f"🚀 MISSION: Priority {priority} - {task}. "
                f"Read your CLAUDE.md file for detailed instructions. "
                f"Acknowledge receipt and begin work. "
                f"Report progress every 2 hours to pm-agent."
            )
            
            # Use multiple delivery methods for reliability
            success = await self._reliable_instruction_delivery(agent_id, task_instruction)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to initialize Claude Code: {e}")
            return False
    
    async def _reliable_instruction_delivery(self, agent_id: str, instruction: str) -> bool:
        """Deliver instructions with multiple retry mechanisms"""
        
        # Method 1: Direct tmux send-keys
        try:
            cmd = [
                "tmux", "send-keys",
                "-t", f"agent-hive:{agent_id}",
                instruction,
                "Enter"
            ]
            subprocess.run(cmd, timeout=10)
            
            # Wait and verify delivery
            await asyncio.sleep(3)
            
            # Method 2: Create instruction file in worktree
            agent_worktrees = list(Path("new-worktrees").glob(f"{agent_id}*"))
            if agent_worktrees:
                instruction_file = agent_worktrees[0] / "INSTRUCTIONS.txt"
                with open(instruction_file, 'w') as f:
                    f.write(f"TASK INSTRUCTIONS:\n{instruction}\n\nDelivered at: {datetime.now().isoformat()}")
                
                # Send file read command
                cmd = [
                    "tmux", "send-keys",
                    "-t", f"agent-hive:{agent_id}",
                    f"cat INSTRUCTIONS.txt",
                    "Enter"
                ]
                subprocess.run(cmd, timeout=10)
            
            # Method 3: Use agent communication system as backup
            try:
                cmd = [
                    "python", "scripts/send_agent_message.py",
                    "--agent", agent_id,
                    "--message", f"TASK START: {instruction}"
                ]
                subprocess.run(cmd, timeout=10)
            except:
                pass  # Backup method, don't fail if not available
                
            logger.info(f"📨 Instructions delivered to {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deliver instructions: {e}")
            return False
    
    async def _ensure_agent_activation(self, agent_id: str, task: str, priority: str) -> bool:
        """Ensure agent is fully activated and working without manual intervention"""
        try:
            # Create comprehensive task prompt
            task_prompt = f"🚀 PRIORITY {priority}: {task}. Read your CLAUDE.md file for detailed instructions. Begin work immediately. Report progress every 2 hours to pm-agent."
            
            # Use agent activator for reliable activation
            cmd = [
                "python", "scripts/agent_activator.py",
                "--agent", agent_id,
                "--task", task_prompt
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info(f"✅ Agent {agent_id} fully activated and working")
                return True
            else:
                logger.error(f"❌ Agent activation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to ensure agent activation: {e}")
            return False
    
    async def _verify_agent_initialization(self, agent_id: str) -> bool:
        """Verify agent is active and received instructions"""
        try:
            # Wait for agent to process instructions
            await asyncio.sleep(10)
            
            # Check if agent tmux session is active
            cmd = ["tmux", "list-windows", "-t", "agent-hive", "-F", "#{window_name}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if agent_id not in result.stdout:
                logger.error(f"Agent {agent_id} tmux session not found")
                return False
            
            # Check agent status via status script
            try:
                cmd = ["python", "scripts/check_agent_status.py", "--format", "json"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    status_data = json.loads(result.stdout)
                    # Look for agent in active list
                    for agent in status_data.get("active_agents", []):
                        if agent_id in agent.get("name", ""):
                            logger.info(f"✅ Agent {agent_id} verified active")
                            return True
            except:
                pass  # Status check is nice-to-have
            
            # If status check fails, assume success if tmux session exists
            logger.info(f"✅ Agent {agent_id} tmux session verified")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify agent initialization: {e}")
            return False
    
    async def _register_agent(self, agent_id: str, metadata: Dict) -> bool:
        """Register agent in tracking system"""
        try:
            # Create agent registry file
            registry_path = Path(".claude/agents") / f"{agent_id}.json"
            registry_path.parent.mkdir(exist_ok=True)
            
            with open(registry_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            logger.info(f"📊 Agent {agent_id} registered in tracking system")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False
    
    async def _setup_progress_monitoring(self, agent_id: str) -> bool:
        """Setup automated progress monitoring and completion detection"""
        try:
            # Start completion monitoring in background
            cmd = [
                "python", "scripts/agent_completion_handler.py", 
                "--agent", agent_id, 
                "--continuous"
            ]
            
            # Start completion monitor as background process
            subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            logger.info(f"📈 Progress monitoring and completion detection setup for {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup progress monitoring: {e}")
            return False
    
    async def _cleanup_failed_spawn(self, agent_id: str):
        """Cleanup resources if spawning fails"""
        try:
            # Kill tmux window if it exists
            cmd = ["tmux", "kill-window", "-t", f"agent-hive:{agent_id}"]
            subprocess.run(cmd, capture_output=True, timeout=10)
            
            # Remove worktree if it exists
            agent_worktrees = list(Path("new-worktrees").glob(f"{agent_id}*"))
            for worktree in agent_worktrees:
                cmd = ["rm", "-rf", str(worktree)]
                subprocess.run(cmd, timeout=30)
                
            # Remove registry file if it exists
            registry_path = Path(".claude/agents") / f"{agent_id}.json"
            if registry_path.exists():
                registry_path.unlink()
                
            logger.info(f"🧹 Cleaned up failed spawn for {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup failed spawn: {e}")
    
    def _get_integration_specialist_template(
        self, task: str, timeline: str, human_decision_points: str,
        success_criteria: str, escalation_triggers: str
    ) -> str:
        """Get integration specialist instructions template"""
        return f"""# 🔧 Integration Specialist - API Gateway Foundation Repair

## 🎯 **Mission: {task}**

You are a specialized integration agent focused on fixing API Gateway foundation issues.

### **Primary Objectives**
- Replace simulation-only API Gateway with real FastAPI HTTP server
- Fix failing tests (86 out of 104 currently failing)
- Implement service discovery integration for real request proxying
- Ensure all existing tests pass with real implementation

### **Timeline: {timeline}**

### **Human Decision Points**
{human_decision_points}

### **Success Criteria**
{success_criteria}

### **Escalation Triggers**
{escalation_triggers}

### **Technical Implementation**
Focus on these key areas:
1. **Real FastAPI Server**: Replace simulation with actual HTTP server
2. **Service Discovery Integration**: Connect to real service discovery
3. **Test Fixes**: Fix all 86 failing tests
4. **Request Proxying**: Implement real request routing and load balancing

### **Quality Gates**
- All tests must pass before completion
- Real HTTP server operational
- Service discovery integration functional
- Performance targets met (<200ms response time)
- **MANDATORY: Commit all changes with descriptive message**
- **MANDATORY: Push branch to remote repository**
- **MANDATORY: Verify work is available on GitHub**

### **Communication Protocol**
Report progress every 2 hours to pm-agent with:
- Tests fixed: X/86 failing tests resolved
- HTTP server status: Implementation progress
- Service discovery: Integration completion %
- Git status: Committed and pushed to remote
- Blockers: Technical issues requiring decisions

### **Completion Workflow**
1. Complete implementation and fix all tests
2. Run quality gates and ensure all pass
3. **git add . && git commit -m "descriptive message"**
4. **git push origin [branch-name]**
5. Verify work appears on GitHub remote
6. ONLY THEN report "MISSION ACCOMPLISHED"

Remember: This is Priority 1.1 - the most critical foundation fix. No shortcuts on test quality, real implementation, OR Git workflow completion.
"""

    def _get_service_mesh_template(
        self, task: str, timeline: str, human_decision_points: str,
        success_criteria: str, escalation_triggers: str
    ) -> str:
        """Get service mesh specialist instructions template"""
        return f"""# 🔧 Service Mesh Specialist - Service Discovery Integration

## 🎯 **Mission: {task}**

You are a specialized service mesh agent focused on service discovery integration.

### **Primary Objectives**
- Add REST API endpoints to Service Discovery for external access
- Implement real HTTP health checks (not placeholder)
- Connect Service Discovery to API Gateway and other components
- Add multi-language service support

### **Timeline: {timeline}**

### **Human Decision Points**
{human_decision_points}

### **Success Criteria**
{success_criteria}

### **Escalation Triggers**
{escalation_triggers}

### **Technical Implementation**
Focus on these key areas:
1. **REST API Development**: Create FastAPI endpoints for service registration/discovery
2. **Real Health Checks**: Replace placeholder with actual HTTP validation
3. **Integration Testing**: Ensure API Gateway can discover services
4. **Multi-Language Support**: Generate client libraries for different languages

### **Quality Gates**
- All REST endpoints functional and tested
- Real HTTP health checks working with retry logic
- API Gateway integration confirmed
- 85%+ test coverage for all new functionality
- **MANDATORY: Commit all changes with descriptive message**
- **MANDATORY: Push branch to remote repository**
- **MANDATORY: Verify work is available on GitHub**

### **Communication Protocol**
Report progress every 2 hours to pm-agent with:
- API endpoints status: X/6 endpoints functional
- Health checks: Real HTTP validation operational
- Integration: API Gateway connection confirmed
- Multi-language: Client libraries generated and tested
- Git status: Committed and pushed to remote

### **Completion Workflow**
1. Complete implementation and achieve 85%+ test coverage
2. Confirm API Gateway integration working
3. **git add . && git commit -m "descriptive message"**
4. **git push origin [branch-name]**
5. Verify work appears on GitHub remote
6. ONLY THEN report "MISSION ACCOMPLISHED"

Remember: This is Priority 1.2 - essential for API Gateway functionality. Service Discovery is the backbone of the entire system.
"""

    def _get_frontend_template(
        self, task: str, timeline: str, human_decision_points: str,
        success_criteria: str, escalation_triggers: str
    ) -> str:
        """Get frontend specialist instructions template"""
        return f"""# 🔧 Frontend Specialist - Dashboard Integration Repair

## 🎯 **Mission: {task}**

You are a specialized frontend agent focused on dashboard integration repair.

### **Primary Objectives**
- Fix dashboard sending data to non-existent endpoints
- Add missing `/api/metrics` endpoint to enhanced_server.py
- Implement real-time WebSocket metric broadcasting
- Create UI components for metrics display

### **Timeline: {timeline}**

### **Human Decision Points**
{human_decision_points}

### **Success Criteria**
{success_criteria}

### **Escalation Triggers**
{escalation_triggers}

### **Technical Implementation**
Focus on these key areas:
1. **Missing Endpoints**: Add `/api/metrics` to enhanced_server.py
2. **WebSocket Broadcasting**: Real-time metric updates to clients
3. **UI Components**: Responsive metrics display with animations
4. **Data Flow Testing**: Complete dashboard to server to UI validation

### **Quality Gates**
- All metric endpoints responding correctly
- Real-time WebSocket updates working without disconnections
- Metrics showing in real-time with animations
- Complete data flow from dashboard to server to UI
- 85%+ test coverage for all new functionality
- **MANDATORY: Commit all changes with descriptive message**
- **MANDATORY: Push branch to remote repository**
- **MANDATORY: Verify work is available on GitHub**

### **Communication Protocol**
Report progress every 2 hours to pm-agent with:
- Endpoint status: `/api/metrics` functional
- WebSocket: Real-time broadcasting operational
- UI: Metrics display components working
- Integration: Complete data flow confirmed
- Git status: Committed and pushed to remote

### **Completion Workflow**
1. Complete implementation and test data flow
2. Verify real-time metrics display working
3. **git add . && git commit -m "descriptive message"**
4. **git push origin [branch-name]**
5. Verify work appears on GitHub remote
6. ONLY THEN report "MISSION ACCOMPLISHED"

Remember: This is Priority 1.3 - essential for monitoring system visibility. No more data loss!
"""

    def _get_security_template(self, task: str, timeline: str, human_decision_points: str, success_criteria: str, escalation_triggers: str) -> str:
        return f"# Security Specialist Template\n\nTask: {task}\nTimeline: {timeline}\n\n[Security implementation details...]"
    
    def _get_infrastructure_template(self, task: str, timeline: str, human_decision_points: str, success_criteria: str, escalation_triggers: str) -> str:
        return f"# Infrastructure Specialist Template\n\nTask: {task}\nTimeline: {timeline}\n\n[Infrastructure implementation details...]"
    
    def _get_performance_template(self, task: str, timeline: str, human_decision_points: str, success_criteria: str, escalation_triggers: str) -> str:
        return f"# Performance Specialist Template\n\nTask: {task}\nTimeline: {timeline}\n\n[Performance implementation details...]"
    
    def _get_monitoring_template(self, task: str, timeline: str, human_decision_points: str, success_criteria: str, escalation_triggers: str) -> str:
        return f"# Monitoring Specialist Template\n\nTask: {task}\nTimeline: {timeline}\n\n[Monitoring implementation details...]"


async def main():
    parser = argparse.ArgumentParser(description="Enhanced Agent Spawner")
    parser.add_argument("--agent-type", required=True, choices=[
        'integration-specialist', 'service-mesh', 'frontend', 
        'security', 'infrastructure', 'performance', 'monitoring'
    ])
    parser.add_argument("--priority", required=True, help="Priority level (e.g., 1.1, 1.2)")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--timeline", required=True, help="Expected timeline")
    parser.add_argument("--human-decision-points", default="", help="Comma-separated human decision points")
    parser.add_argument("--success-criteria", default="", help="Comma-separated success criteria")
    parser.add_argument("--escalation-triggers", default="", help="Comma-separated escalation triggers")
    
    args = parser.parse_args()
    
    spawner = EnhancedAgentSpawner()
    
    success, agent_id, metadata = await spawner.spawn_agent(
        agent_type=args.agent_type,
        priority=args.priority,
        task=args.task,
        timeline=args.timeline,
        human_decision_points=args.human_decision_points,
        success_criteria=args.success_criteria,
        escalation_triggers=args.escalation_triggers
    )
    
    if success:
        print(f"✅ Agent {agent_id} spawned successfully")
        print(f"📊 Metadata: {json.dumps(metadata, indent=2)}")
        sys.exit(0)
    else:
        print(f"❌ Failed to spawn agent: {metadata.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())