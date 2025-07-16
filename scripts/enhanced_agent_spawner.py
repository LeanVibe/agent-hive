#!/usr/bin/env python3
"""
Enhanced Agent Spawner with Hybrid Communication Protocol Integration

Automatically generates CLAUDE.md files with embedded communication protocol
for all newly spawned agents.
"""

import os
import subprocess
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid


class EnhancedAgentSpawner:
    """Enhanced agent spawner with automatic protocol integration."""
    
    def __init__(self, base_dir: str = ".", session_name: str = "agent-hive"):
        self.base_dir = Path(base_dir)
        self.session_name = session_name
        self.templates_dir = self.base_dir / "templates"
        self.worktrees_dir = self.base_dir / "worktrees"
        
        # Ensure directories exist
        self.templates_dir.mkdir(exist_ok=True)
        self.worktrees_dir.mkdir(exist_ok=True)
        
        # Agent type configurations
        self.agent_configs = {
            "integration-specialist": {
                "description": "API Gateway and Service Integration Specialist",
                "mission": "Replace simulation API Gateway with real FastAPI HTTP server and fix failing tests",
                "priority": 1.1,
                "timeline": "2-3 days",
                "specialization": "API integration, service discovery, HTTP servers, microservices"
            },
            "frontend-dashboard": {
                "description": "Frontend Dashboard and UI Specialist", 
                "mission": "Build responsive dashboard for agent monitoring and system visualization",
                "priority": 1.2,
                "timeline": "3-4 days",
                "specialization": "React, D3.js, real-time UI, data visualization"
            },
            "service-mesh": {
                "description": "Service Mesh and Infrastructure Specialist",
                "mission": "Implement service mesh architecture with load balancing and discovery",
                "priority": 1.3,
                "timeline": "2-3 days", 
                "specialization": "Service mesh, load balancing, infrastructure, networking"
            },
            "monitoring-system": {
                "description": "Monitoring and Observability Specialist",
                "mission": "Build comprehensive monitoring system with metrics and alerting",
                "priority": 1.4,
                "timeline": "3-4 days",
                "specialization": "Monitoring, metrics, logging, observability, alerting"
            },
            "security-hardening": {
                "description": "Security and Authentication Specialist",
                "mission": "Implement comprehensive security framework with authentication and authorization",
                "priority": 1.5,
                "timeline": "3-4 days",
                "specialization": "Security, authentication, authorization, encryption, compliance"
            },
            "documentation-agent": {
                "description": "Documentation and Knowledge Management Specialist",
                "mission": "Create comprehensive documentation and developer experience resources",
                "priority": 2.0,
                "timeline": "4-5 days",
                "specialization": "Technical writing, API documentation, developer experience"
            },
            "quality-assurance": {
                "description": "Quality Assurance and Testing Specialist", 
                "mission": "Implement comprehensive testing framework and quality gates",
                "priority": 2.1,
                "timeline": "3-4 days",
                "specialization": "Testing frameworks, quality assurance, automation, CI/CD"
            },
            "performance-optimization": {
                "description": "Performance and Scalability Specialist",
                "mission": "Optimize system performance and implement scalability solutions",
                "priority": 2.2,
                "timeline": "3-4 days", 
                "specialization": "Performance tuning, scalability, caching, optimization"
            }
        }
    
    def generate_claude_md(self, agent_type: str, task_description: str = None, 
                          priority: float = None) -> str:
        """Generate CLAUDE.md content with embedded communication protocol."""
        
        if agent_type not in self.agent_configs:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        config = self.agent_configs[agent_type]
        agent_name = f"{agent_type}-{datetime.now().strftime('%b-%d-%H%M')}"
        
        # Use provided values or defaults from config
        description = config["description"]
        mission = task_description or config["mission"]
        agent_priority = priority or config["priority"]
        timeline = config["timeline"]
        specialization = config["specialization"]
        
        # Load template
        template_file = self.templates_dir / "agent_claude_template.md"
        if template_file.exists():
            template_content = template_file.read_text()
        else:
            # Fallback template if file doesn't exist
            template_content = self._get_fallback_template()
        
        # Generate agent-specific instructions
        agent_specific_content = self._generate_agent_specific_content(
            agent_type, config, mission, timeline, specialization
        )
        
        additional_instructions = self._generate_additional_instructions(
            agent_type, config
        )
        
        # Replace template variables
        claude_content = template_content.format(
            agent_name=agent_name,
            agent_description=description,
            mission_description=mission,
            agent_specific_content=agent_specific_content,
            additional_agent_instructions=additional_instructions
        )
        
        return claude_content
    
    def _generate_agent_specific_content(self, agent_type: str, config: Dict, 
                                        mission: str, timeline: str, 
                                        specialization: str) -> str:
        """Generate agent-specific content section."""
        
        content = f"""## **Agent Identity**
**Role**: {config['description']}
**Specialization**: {specialization}
**Priority**: {config['priority']} ({"Critical" if config['priority'] < 2.0 else "High"})
**Timeline**: {timeline}

## **Primary Mission**
{mission}

## **Key Responsibilities**"""
        
        # Add agent-type specific responsibilities
        if agent_type == "integration-specialist":
            content += """
- Replace simulation API Gateway with production FastAPI HTTP server
- Fix failing tests (target: 100% test pass rate)
- Implement real service discovery integration
- Ensure request proxying and load balancing functionality
- Performance optimization (<200ms response time)"""
            
        elif agent_type == "frontend-dashboard":
            content += """
- Build responsive React-based dashboard for system monitoring
- Implement real-time data visualization with D3.js
- Create agent status monitoring interface
- Design system health and metrics display
- Ensure mobile-responsive design"""
            
        elif agent_type == "service-mesh":
            content += """
- Implement service mesh architecture for microservices
- Configure load balancing and service discovery
- Set up inter-service communication protocols
- Implement circuit breakers and retry logic
- Configure networking and routing policies"""
            
        elif agent_type == "monitoring-system":
            content += """
- Build comprehensive metrics collection system
- Implement real-time alerting and notification system
- Create system health monitoring dashboard
- Set up log aggregation and analysis
- Configure performance monitoring and profiling"""
            
        elif agent_type == "security-hardening":
            content += """
- Implement comprehensive authentication system
- Set up authorization and role-based access control
- Configure encryption for data in transit and at rest
- Implement security scanning and vulnerability assessment
- Set up compliance monitoring and reporting"""
            
        elif agent_type == "documentation-agent":
            content += """
- Create comprehensive API documentation
- Build developer onboarding guides
- Implement interactive documentation with examples
- Create system architecture documentation
- Set up automated documentation generation"""
            
        elif agent_type == "quality-assurance":
            content += """
- Implement comprehensive testing framework
- Set up automated quality gates and CI/CD pipelines
- Create performance and load testing suites
- Implement code quality monitoring
- Set up automated security and compliance testing"""
            
        elif agent_type == "performance-optimization":
            content += """
- Analyze system performance bottlenecks
- Implement caching strategies and optimization
- Configure load balancing and scaling policies
- Optimize database queries and data access
- Implement monitoring and profiling tools"""
        
        return content
    
    def _generate_additional_instructions(self, agent_type: str, config: Dict) -> str:
        """Generate additional agent-specific instructions."""
        
        instructions = f"""
## **Quality Gates**
- All tests must pass before task completion
- Code must meet quality standards (linting, formatting)
- Performance targets must be achieved
- Documentation must be updated
- Security requirements must be satisfied

## **Success Criteria**"""
        
        # Add agent-specific success criteria
        if agent_type == "integration-specialist":
            instructions += """
- ✅ Real FastAPI HTTP server operational
- ✅ All tests passing (100% pass rate)
- ✅ Service discovery integration functional
- ✅ Response time <200ms achieved
- ✅ Load balancing operational"""
            
        elif agent_type == "frontend-dashboard":
            instructions += """
- ✅ Responsive dashboard deployed and functional
- ✅ Real-time data visualization working
- ✅ Agent monitoring interface complete
- ✅ Mobile compatibility achieved
- ✅ Performance metrics <2s load time"""
            
        # Add more agent-specific criteria as needed
        
        instructions += f"""

## **Escalation Triggers**
- Technical blockers persisting >30 minutes
- Test failures after 4 hours of debugging
- Performance targets not achievable with current approach
- Integration conflicts with other system components
- Security vulnerabilities discovered

## **Human Decision Points**
- Architecture changes affecting system design
- Technology selection requiring approval
- Resource allocation exceeding timeline estimates
- Security policies requiring compliance review
- Integration approaches affecting other agents

## **Communication Schedule**
- **Startup**: Send [ACK] within 1 minute of spawning
- **Progress**: Respond to pings within 2 minutes with detailed status
- **Updates**: Push [URGENT] immediately for completion, blockers, conflicts, PR ready
- **Completion**: Final deliverable summary with evidence and metrics

**Remember**: Priority {config['priority']} agent - Critical path component requiring {config['timeline']} completion."""
        
        return instructions
    
    def _get_fallback_template(self) -> str:
        """Fallback template if template file doesn't exist."""
        return """# {agent_name} - {agent_description}

## 🎯 **Mission: {mission_description}**

{agent_specific_content}

# 🚨 HYBRID COMMUNICATION PROTOCOL - MANDATORY

## 📡 **COORDINATION SYSTEM RULES**

### **RESPONSE REQUIREMENTS**
1. **Ping Response Time**: RESPOND to main agent pings within **2 minutes maximum**
2. **Acknowledgment Format**: Use `[ACK] - Agent {agent_name} ready - Current task: {{current_task}}`
3. **Status Updates**: Provide clear, actionable status when pinged

### **URGENT UPDATE PROTOCOL**
**IMMEDIATE PUSH REQUIRED** for these events using exact format:
`[URGENT] - {{Description}} - {{Evidence}}`

### **URGENT EVENT CATEGORIES**
1. **Task Completion**: `[URGENT] - Task complete - Evidence`
2. **Critical Blocker**: `[URGENT] - Blocker detected - Details and ETA`
3. **Merge Conflicts**: `[URGENT] - Merge conflict - Files and resolution needed`
4. **PR Ready**: `[URGENT] - PR ready - PR# and status`

{additional_agent_instructions}

**🔗 PROTOCOL ACTIVE**: This communication protocol is active and monitored."""
    
    def create_agent_worktree(self, agent_type: str, task_description: str = None,
                            priority: float = None) -> Dict[str, Any]:
        """Create new agent worktree with protocol-enabled CLAUDE.md."""
        
        if agent_type not in self.agent_configs:
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(self.agent_configs.keys())}")
        
        # Generate unique agent name with timestamp
        timestamp = datetime.now().strftime('%b-%d-%H%M')
        agent_name = f"{agent_type}-{timestamp}"
        branch_name = f"new-work/{agent_name}"
        worktree_path = self.worktrees_dir / agent_name
        
        print(f"🚀 Creating agent worktree: {agent_name}")
        print(f"📁 Path: {worktree_path}")
        print(f"🌿 Branch: {branch_name}")
        
        try:
            # Create git worktree
            result = subprocess.run([
                "git", "worktree", "add", str(worktree_path), "-b", branch_name
            ], cwd=self.base_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Git worktree creation failed: {result.stderr}")
            
            # Generate CLAUDE.md with protocol
            claude_content = self.generate_claude_md(agent_type, task_description, priority)
            claude_file = worktree_path / "CLAUDE.md"
            claude_file.write_text(claude_content)
            
            print(f"✅ Created CLAUDE.md with hybrid communication protocol")
            
            # Initial commit
            subprocess.run([
                "git", "add", "CLAUDE.md"
            ], cwd=worktree_path, check=True)
            
            subprocess.run([
                "git", "commit", "-m", f"feat: Initialize {agent_type} agent with hybrid communication protocol\n\n🤖 Generated with Claude Code\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
            ], cwd=worktree_path, check=True)
            
            print(f"✅ Initial commit created")
            
            # Create agent info
            agent_info = {
                "agent_name": agent_name,
                "agent_type": agent_type,
                "branch_name": branch_name,
                "worktree_path": str(worktree_path),
                "claude_file": str(claude_file),
                "config": self.agent_configs[agent_type],
                "task_description": task_description,
                "priority": priority or self.agent_configs[agent_type]["priority"],
                "created_at": datetime.now().isoformat(),
                "protocol_enabled": True,
                "spawn_id": str(uuid.uuid4())
            }
            
            return agent_info
            
        except Exception as e:
            print(f"❌ Failed to create agent worktree: {e}")
            # Cleanup on failure
            if worktree_path.exists():
                subprocess.run(["git", "worktree", "remove", str(worktree_path), "--force"], 
                             cwd=self.base_dir, capture_output=True)
            raise
    
    def spawn_agent_with_tmux(self, agent_info: Dict[str, Any], 
                            with_prompt: bool = True) -> bool:
        """Spawn agent in tmux with protocol-aware starting prompt."""
        
        agent_name = agent_info["agent_name"]
        worktree_path = agent_info["worktree_path"]
        window_name = f"agent-{agent_name}"
        
        print(f"🔄 Spawning {agent_name} in tmux...")
        
        try:
            # Ensure tmux session exists
            subprocess.run(["tmux", "has-session", "-t", self.session_name], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # Create session if it doesn't exist
            subprocess.run(["tmux", "new-session", "-d", "-s", self.session_name], 
                         check=True)
            print(f"✅ Created tmux session: {self.session_name}")
        
        # Check if window already exists
        result = subprocess.run([
            "tmux", "list-windows", "-t", self.session_name, "-F", "#{window_name}"
        ], capture_output=True, text=True)
        
        if window_name in result.stdout.splitlines():
            print(f"⚠️  Window '{window_name}' already exists, killing...")
            subprocess.run(["tmux", "kill-window", "-t", f"{self.session_name}:{window_name}"])
        
        # Create new window
        subprocess.run([
            "tmux", "new-window", "-t", self.session_name, "-n", window_name, "-c", worktree_path
        ], check=True)
        
        # Start Claude with permissions
        subprocess.run([
            "tmux", "send-keys", "-t", f"{self.session_name}:{window_name}", 
            "claude --dangerously-skip-permissions", "Enter"
        ])
        
        if with_prompt:
            time.sleep(3)  # Wait for Claude to initialize
            
            # Protocol-aware starting prompt
            starting_prompt = self._generate_starting_prompt(agent_info)
            
            # Use buffer method for reliable prompt sending
            subprocess.run(["tmux", "set-buffer", starting_prompt])
            subprocess.run(["tmux", "send-keys", "-t", f"{self.session_name}:{window_name}", "C-c"])
            time.sleep(0.3)
            subprocess.run(["tmux", "paste-buffer", "-t", f"{self.session_name}:{window_name}"])
            time.sleep(0.2)
            subprocess.run(["tmux", "send-keys", "-t", f"{self.session_name}:{window_name}", "Enter"])
            
            print(f"🚀 Protocol-aware starting prompt sent")
        
        print(f"✅ Agent {agent_name} spawned successfully")
        print(f"📋 Window: {window_name}")
        print(f"📁 Directory: {worktree_path}")
        print(f"🔗 Protocol: Hybrid communication enabled")
        
        return True
    
    def _generate_starting_prompt(self, agent_info: Dict[str, Any]) -> str:
        """Generate protocol-aware starting prompt."""
        
        agent_name = agent_info["agent_name"]
        agent_type = agent_info["agent_type"]
        task_description = agent_info.get("task_description", "")
        priority = agent_info["priority"]
        
        prompt = f"""AGENT SPAWN COMPLETE: {agent_name}

🚨 HYBRID COMMUNICATION PROTOCOL ACTIVE

IMMEDIATE ACTIONS REQUIRED:
1. Send acknowledgment: [ACK] - Agent {agent_name} ready - Current task: Initializing {agent_type} implementation
2. Read your CLAUDE.md file for detailed mission instructions and communication protocol
3. Begin implementation of: {task_description or agent_info['config']['mission']}

PROTOCOL REQUIREMENTS:
- Respond to pings within 2 minutes using [ACK] format
- Push urgent updates immediately using [URGENT] format for: task completion, critical blockers, merge conflicts, PR ready
- Provide concrete evidence in all status updates

PRIORITY: {priority} ({"CRITICAL PATH" if priority < 2.0 else "HIGH PRIORITY"})

Your mission details are in CLAUDE.md. Start by sending your [ACK] message, then read your instructions and begin implementation immediately."""
        
        return prompt
    
    def create_and_spawn_agent(self, agent_type: str, task_description: str = None,
                             priority: float = None, spawn_tmux: bool = True,
                             with_prompt: bool = True) -> Dict[str, Any]:
        """Complete agent creation and spawning process."""
        
        print(f"🎯 ENHANCED AGENT SPAWNER: Creating {agent_type}")
        print(f"📋 Task: {task_description or 'Default mission'}")
        print(f"⭐ Priority: {priority or self.agent_configs[agent_type]['priority']}")
        print()
        
        # Create worktree with protocol
        agent_info = self.create_agent_worktree(agent_type, task_description, priority)
        
        # Spawn in tmux if requested
        if spawn_tmux:
            success = self.spawn_agent_with_tmux(agent_info, with_prompt)
            agent_info["spawned"] = success
            agent_info["tmux_window"] = f"agent-{agent_info['agent_name']}"
        else:
            agent_info["spawned"] = False
            agent_info["tmux_window"] = None
        
        print()
        print(f"🎉 AGENT CREATION COMPLETE")
        print(f"📝 Agent: {agent_info['agent_name']}")
        print(f"📁 Path: {agent_info['worktree_path']}")
        print(f"🔗 Protocol: Enabled and active")
        print(f"🚀 Spawned: {'Yes' if agent_info['spawned'] else 'No'}")
        
        return agent_info


def main():
    parser = argparse.ArgumentParser(description="Enhanced Agent Spawner with Communication Protocol")
    parser.add_argument("--agent-type", help="Type of agent to spawn (integration-specialist, frontend-dashboard, etc.)")
    parser.add_argument("--task", help="Specific task description")
    parser.add_argument("--priority", type=float, help="Priority level (lower = higher priority)")
    parser.add_argument("--session", default="agent-hive", help="Tmux session name")
    parser.add_argument("--no-spawn", action="store_true", help="Create worktree only, don't spawn in tmux")
    parser.add_argument("--no-prompt", action="store_true", help="Don't send starting prompt")
    parser.add_argument("--list-types", action="store_true", help="List available agent types")
    parser.add_argument("--generate-template", action="store_true", help="Generate template file")
    
    args = parser.parse_args()
    
    spawner = EnhancedAgentSpawner(session_name=args.session)
    
    if args.list_types:
        print("📋 Available Agent Types:")
        print("=" * 50)
        for agent_type, config in spawner.agent_configs.items():
            print(f"🔧 {agent_type}")
            print(f"   Description: {config['description']}")
            print(f"   Priority: {config['priority']}")
            print(f"   Timeline: {config['timeline']}")
            print(f"   Mission: {config['mission']}")
            print()
        return
    
    if args.generate_template:
        template_file = spawner.templates_dir / "agent_claude_template.md"
        if not template_file.exists():
            # Template should already be created, but regenerate if needed
            print(f"✅ Template file exists at: {template_file}")
        else:
            print(f"📝 Template file found: {template_file}")
        return
    
    # Validate agent type
    if not args.agent_type:
        print("❌ Error: --agent-type is required")
        print("Available types: " + ", ".join(spawner.agent_configs.keys()))
        print("Use --list-types to see detailed descriptions")
        return 1
    
    if args.agent_type not in spawner.agent_configs:
        print(f"❌ Unknown agent type: {args.agent_type}")
        print(f"Available types: {list(spawner.agent_configs.keys())}")
        print("Use --list-types to see detailed descriptions")
        return 1
    
    # Create and spawn agent
    try:
        agent_info = spawner.create_and_spawn_agent(
            agent_type=args.agent_type,
            task_description=args.task,
            priority=args.priority,
            spawn_tmux=not args.no_spawn,
            with_prompt=not args.no_prompt
        )
        
        print()
        print("📊 CREATION SUMMARY:")
        print(json.dumps({
            "agent_name": agent_info["agent_name"],
            "agent_type": agent_info["agent_type"],
            "priority": agent_info["priority"],
            "worktree_path": agent_info["worktree_path"],
            "protocol_enabled": agent_info["protocol_enabled"],
            "spawned": agent_info["spawned"]
        }, indent=2))
        
    except Exception as e:
        print(f"❌ AGENT CREATION FAILED: {e}")
        return 1


if __name__ == "__main__":
    exit(main() or 0)