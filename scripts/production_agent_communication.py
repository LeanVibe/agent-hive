#!/usr/bin/env python3
"""
Production Agent Communication System

REPLACES tmux-based communication with Redis message bus.
Production-grade agent communication with reliability, persistence, and scalability.
"""

import asyncio
import argparse
import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from message_bus import (
    MessageBus, MessageBusConfig, AgentCommunicator, AgentRegistry,
    Message, MessageType, MessagePriority, RetryManager, DeadLetterQueue
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionAgentCommunicationSystem:
    """
    Production agent communication system replacing tmux.
    
    Features:
    - Redis-based message bus with persistence
    - Agent discovery and capability matching
    - Message acknowledgment and retry
    - Dead letter queues for failed messages
    - Real-time monitoring and metrics
    - Horizontal scalability
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize production communication system.
        
        Args:
            redis_url: Redis connection URL
        """
        self.config = MessageBusConfig(redis_url=redis_url)
        self.message_bus = MessageBus(self.config)
        self.registry = AgentRegistry(self.message_bus)
        self.retry_manager = RetryManager(None)  # Will be set after Redis init
        self.dead_letter_queue = DeadLetterQueue(None)  # Will be set after Redis init
        
        # Active agents (replaces tmux windows)
        self.active_agents = [
            "integration-specialist-Jul-16-1220",
            "service-mesh-Jul-16-1221", 
            "frontend-Jul-16-1222",
            "pm-agent-new"
        ]
        
        # Communication statistics
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "task_assignments": 0,
            "agent_discoveries": 0
        }
    
    async def start(self) -> None:
        """Start the production communication system."""
        try:
            logger.info("🚀 Starting production agent communication system...")
            
            # Start message bus
            await self.message_bus.start()
            
            # Initialize reliability components with Redis client
            self.retry_manager = RetryManager(self.message_bus.redis_client)
            self.dead_letter_queue = DeadLetterQueue(self.message_bus.redis_client)
            
            # Start components
            await self.registry.start()
            await self.retry_manager.start()
            
            # Register message handlers
            self._register_handlers()
            
            logger.info("✅ Production communication system started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start communication system: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the communication system."""
        logger.info("🛑 Stopping production communication system...")
        
        await self.retry_manager.stop()
        await self.registry.stop()
        await self.message_bus.stop()
        
        logger.info("✅ Production communication system stopped")
    
    async def send_message_to_agent(self, agent_name: str, message: str, 
                                   priority: str = "normal", wait_response: bool = False) -> bool:
        """
        Send a message to an agent (REPLACES tmux send-keys).
        
        Args:
            agent_name: Target agent name
            message: Message content
            priority: Message priority (low, normal, high, urgent, critical)
            wait_response: Wait for response
            
        Returns:
            True if message sent successfully
        """
        try:
            # Map priority string to enum
            priority_map = {
                "low": MessagePriority.LOW,
                "normal": MessagePriority.NORMAL,
                "high": MessagePriority.HIGH,
                "urgent": MessagePriority.URGENT,
                "critical": MessagePriority.CRITICAL
            }
            
            msg_priority = priority_map.get(priority.lower(), MessagePriority.NORMAL)
            
            # Create message
            await self.message_bus.send_direct_message(
                target_agent=agent_name,
                message_type=MessageType.SYSTEM_COMMAND,
                payload={
                    "command": "execute",
                    "content": message,
                    "source": "human_operator",
                    "timestamp": asyncio.get_event_loop().time()
                },
                priority=msg_priority
            )
            
            self.stats["messages_sent"] += 1
            
            print(f"✅ Message sent to {agent_name}: {message[:50]}{'...' if len(message) > 50 else ''}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send message to {agent_name}: {e}")
            return False
    
    async def assign_task_automatically(self, task_description: str, 
                                       required_skills: List[str],
                                       confidence_threshold: float = 0.75) -> Optional[str]:
        """
        Automatically assign task to best available agent.
        
        Args:
            task_description: Task description
            required_skills: Required skills
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            Assigned agent name or None
        """
        try:
            # Find capable agents
            capable_agents = await self.registry.find_capable_agents(required_skills)
            
            if not capable_agents:
                print(f"❌ No agents found with required skills: {required_skills}")
                return None
            
            # Select best agent (first available)
            best_agent = capable_agents[0]
            
            # Create task assignment
            task_id = f"task_{int(asyncio.get_event_loop().time())}"
            
            await self.message_bus.send_direct_message(
                target_agent=best_agent.name,
                message_type=MessageType.TASK_ASSIGNMENT,
                payload={
                    "task_id": task_id,
                    "description": task_description,
                    "required_skills": required_skills,
                    "confidence_threshold": confidence_threshold,
                    "priority": "high",
                    "assigned_at": asyncio.get_event_loop().time()
                },
                priority=MessagePriority.HIGH
            )
            
            self.stats["task_assignments"] += 1
            
            print(f"✅ Assigned task {task_id} to {best_agent.name}")
            print(f"📋 Task: {task_description}")
            print(f"🛠️ Skills: {', '.join(required_skills)}")
            
            return best_agent.name
            
        except Exception as e:
            print(f"❌ Failed to assign task: {e}")
            return None
    
    async def broadcast_system_command(self, command: str, args: Dict[str, Any]) -> int:
        """
        Broadcast system command to all agents.
        
        Args:
            command: System command
            args: Command arguments
            
        Returns:
            Number of agents notified
        """
        try:
            await self.message_bus.broadcast_message(
                message_type=MessageType.SYSTEM_COMMAND,
                payload={
                    "command": command,
                    "args": args,
                    "broadcast": True,
                    "timestamp": asyncio.get_event_loop().time()
                },
                target_group="all",
                priority=MessagePriority.HIGH
            )
            
            active_agents = await self.registry.get_all_agents()
            agent_count = len(active_agents)
            
            print(f"📡 Broadcast '{command}' to {agent_count} agents")
            return agent_count
            
        except Exception as e:
            print(f"❌ Failed to broadcast command: {e}")
            return 0
    
    async def get_agent_status(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get agent status information.
        
        Args:
            agent_name: Specific agent name or None for all agents
            
        Returns:
            Agent status information
        """
        try:
            if agent_name:
                agent_info = await self.registry.get_agent_info(agent_name)
                if agent_info:
                    return {
                        "name": agent_info.name,
                        "status": agent_info.status,
                        "capabilities": agent_info.capabilities,
                        "current_task": agent_info.current_task,
                        "last_heartbeat": agent_info.last_heartbeat.isoformat() if agent_info.last_heartbeat else None
                    }
                else:
                    return {"error": f"Agent {agent_name} not found"}
            else:
                all_agents = await self.registry.get_all_agents()
                return {
                    "total_agents": len(all_agents),
                    "agents": [
                        {
                            "name": agent.name,
                            "status": agent.status,
                            "capabilities": agent.capabilities,
                            "current_task": agent.current_task,
                            "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
                        }
                        for agent in all_agents
                    ]
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    async def test_communication_system(self) -> Dict[str, Any]:
        """
        Test the communication system with all 4 active agents.
        
        Returns:
            Test results
        """
        print("🚀 Testing production communication system...")
        
        results = {
            "agents_tested": 0,
            "messages_sent": 0,
            "tasks_assigned": 0,
            "system_commands": 0,
            "errors": []
        }
        
        try:
            # Test 1: Agent discovery
            print("\n1️⃣ Testing agent discovery...")
            all_agents = await self.registry.get_all_agents()
            print(f"📊 Found {len(all_agents)} active agents")
            
            # Test 2: Direct messaging
            print("\n2️⃣ Testing direct messaging...")
            test_tasks = [
                {
                    "description": "Fix API Gateway integration tests",
                    "skills": ["python", "testing", "fastapi"],
                    "target": "integration-specialist-Jul-16-1220"
                },
                {
                    "description": "Optimize service mesh performance", 
                    "skills": ["microservices", "performance", "kubernetes"],
                    "target": "service-mesh-Jul-16-1221"
                },
                {
                    "description": "Update frontend dashboard components",
                    "skills": ["react", "frontend", "ui/ux"],
                    "target": "frontend-Jul-16-1222"
                }
            ]
            
            for task in test_tasks:
                success = await self.send_message_to_agent(
                    task["target"],
                    f"Test task: {task['description']}"
                )
                if success:
                    results["messages_sent"] += 1
                else:
                    results["errors"].append(f"Failed to message {task['target']}")
            
            # Test 3: Automated task assignment
            print("\n3️⃣ Testing automated task assignment...")
            for task in test_tasks:
                assigned_agent = await self.assign_task_automatically(
                    task["description"],
                    task["skills"]
                )
                if assigned_agent:
                    results["tasks_assigned"] += 1
                else:
                    results["errors"].append(f"Failed to assign task: {task['description']}")
            
            # Test 4: System commands
            print("\n4️⃣ Testing system commands...")
            commands_sent = await self.broadcast_system_command("ping", {"test": True})
            results["system_commands"] = commands_sent
            
            # Test 5: PM workload reduction simulation
            print("\n5️⃣ Testing PM workload reduction...")
            pm_tasks = [
                "Monitor integration progress",
                "Coordinate cross-team communication", 
                "Track milestone completion",
                "Generate status reports"
            ]
            
            automated_count = 0
            for task in pm_tasks:
                # Simulate automated handling
                if "Monitor" in task or "Track" in task:
                    print(f"🤖 Automated: {task}")
                    automated_count += 1
                else:
                    print(f"👤 Manual: {task}")
            
            automation_rate = automated_count / len(pm_tasks)
            print(f"📊 PM Automation Rate: {automation_rate:.1%}")
            
            results["agents_tested"] = len(self.active_agents)
            results["pm_automation_rate"] = automation_rate
            
            print(f"\n✅ Communication system test completed!")
            print(f"📊 Results: {json.dumps(results, indent=2)}")
            
            return results
            
        except Exception as e:
            error_msg = f"Communication test failed: {e}"
            print(f"❌ {error_msg}")
            results["errors"].append(error_msg)
            return results
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            bus_stats = await self.message_bus.get_statistics()
            retry_stats = await self.retry_manager.get_retry_stats()
            dl_stats = await self.dead_letter_queue.get_statistics()
            
            return {
                "communication_stats": self.stats,
                "message_bus": bus_stats,
                "reliability": {
                    "retry_queue": retry_stats,
                    "dead_letter": dl_stats
                },
                "system_health": "healthy" if bus_stats["redis_connected"] else "degraded"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _register_handlers(self) -> None:
        """Register message handlers."""
        
        async def handle_task_completion(message: Message) -> None:
            """Handle task completion notifications."""
            task_data = message.payload
            print(f"✅ Task completed: {task_data.get('task_id')} by {message.source_agent}")
            self.stats["messages_received"] += 1
        
        async def handle_agent_heartbeat(message: Message) -> None:
            """Handle agent heartbeats."""
            heartbeat_data = message.payload
            agent_name = heartbeat_data.get("agent_name")
            status = heartbeat_data.get("status")
            # print(f"💓 Heartbeat from {agent_name}: {status}")
            self.stats["messages_received"] += 1
        
        async def handle_error_report(message: Message) -> None:
            """Handle error reports."""
            error_data = message.payload
            print(f"🚨 Error from {message.source_agent}: {error_data.get('error')}")
            self.stats["messages_received"] += 1
        
        # Register handlers
        self.message_bus.register_handler(MessageType.TASK_COMPLETION, handle_task_completion)
        self.message_bus.register_handler(MessageType.AGENT_HEARTBEAT, handle_agent_heartbeat)
        self.message_bus.register_handler(MessageType.ERROR_REPORT, handle_error_report)


async def main():
    """Main CLI interface for production agent communication."""
    parser = argparse.ArgumentParser(
        description="Production Agent Communication System (replaces tmux)"
    )
    
    # Connection options
    parser.add_argument("--redis-url", default="redis://localhost:6379/0",
                       help="Redis connection URL")
    
    # Communication options
    parser.add_argument("--agent", help="Target agent name")
    parser.add_argument("--message", help="Message to send")
    parser.add_argument("--priority", default="normal", 
                       choices=["low", "normal", "high", "urgent", "critical"],
                       help="Message priority")
    
    # Task assignment
    parser.add_argument("--assign-task", help="Task description for automatic assignment")
    parser.add_argument("--skills", nargs="+", help="Required skills for task assignment")
    parser.add_argument("--confidence", type=float, default=0.75, 
                       help="Confidence threshold (0.0-1.0)")
    
    # System operations
    parser.add_argument("--broadcast", help="Broadcast system command")
    parser.add_argument("--args", help="Command arguments (JSON format)")
    parser.add_argument("--status", nargs="?", const="all", 
                       help="Get agent status (agent name or 'all')")
    
    # Testing and monitoring
    parser.add_argument("--test-system", action="store_true",
                       help="Test communication system with all agents")
    parser.add_argument("--stats", action="store_true",
                       help="Show system statistics")
    parser.add_argument("--monitor", action="store_true",
                       help="Start monitoring mode")
    
    args = parser.parse_args()
    
    # Initialize communication system
    comm_system = ProductionAgentCommunicationSystem(args.redis_url)
    
    try:
        await comm_system.start()
        
        # Handle different operations
        if args.test_system:
            results = await comm_system.test_communication_system()
            sys.exit(0 if not results.get("errors") else 1)
        
        elif args.assign_task:
            if not args.skills:
                print("❌ --skills required for task assignment")
                sys.exit(1)
            
            assigned_agent = await comm_system.assign_task_automatically(
                args.assign_task, args.skills, args.confidence
            )
            sys.exit(0 if assigned_agent else 1)
        
        elif args.broadcast:
            command_args = json.loads(args.args) if args.args else {}
            count = await comm_system.broadcast_system_command(args.broadcast, command_args)
            print(f"📡 Command broadcast to {count} agents")
            sys.exit(0)
        
        elif args.status:
            agent_name = None if args.status == "all" else args.status
            status = await comm_system.get_agent_status(agent_name)
            print(json.dumps(status, indent=2))
            sys.exit(0)
        
        elif args.stats:
            stats = await comm_system.get_system_statistics()
            print(json.dumps(stats, indent=2))
            sys.exit(0)
        
        elif args.monitor:
            print("📊 Starting monitoring mode (Ctrl+C to stop)...")
            try:
                while True:
                    stats = await comm_system.get_system_statistics()
                    print(f"\r📊 Messages: {stats['communication_stats']['messages_sent']}/{stats['communication_stats']['messages_received']} | "
                          f"Agents: {stats['message_bus']['agents_connected']} | "
                          f"Health: {stats['system_health']}", end="", flush=True)
                    await asyncio.sleep(2)
            except KeyboardInterrupt:
                print("\n✅ Monitoring stopped")
            sys.exit(0)
        
        elif args.agent and args.message:
            success = await comm_system.send_message_to_agent(
                args.agent, args.message, args.priority
            )
            sys.exit(0 if success else 1)
        
        else:
            parser.print_help()
            print("\n🚀 Examples:")
            print("  # Send message to agent")
            print("  python production_agent_communication.py --agent integration-specialist-Jul-16-1220 --message 'Fix API tests'")
            print("")
            print("  # Assign task automatically")
            print("  python production_agent_communication.py --assign-task 'Optimize performance' --skills python microservices")
            print("")
            print("  # Test entire system")
            print("  python production_agent_communication.py --test-system")
            print("")
            print("  # Monitor system")
            print("  python production_agent_communication.py --monitor")
            sys.exit(1)
    
    finally:
        await comm_system.stop()


if __name__ == "__main__":
    asyncio.run(main())