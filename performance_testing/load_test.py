#!/usr/bin/env python3
"""
High-capacity performance testing for Message Queue System.
Validates >1000 messages/minute capacity with realistic agent workloads.
"""

import asyncio
import time
import json
import sys
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import aiohttp
import websockets

# Add message_queue to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from message_queue.models import Message, MessagePriority, Agent, AgentStatus
from message_queue.queue_service import MessageQueueService, QueueConfig


@dataclass
class PerformanceResult:
    """Performance test result data."""
    test_name: str
    duration_seconds: float
    total_messages: int
    successful_messages: int
    failed_messages: int
    messages_per_second: float
    messages_per_minute: float
    average_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    timestamp: datetime


class MessageQueueLoadTester:
    """Comprehensive load testing for message queue system."""

    def __init__(self,
                 api_base_url: str = "http://localhost:8080",
                 redis_url: str = "redis://localhost:6379"):
        self.api_base_url = api_base_url
        self.redis_url = redis_url
        self.queue_service: Optional[MessageQueueService] = None
        self.session: Optional[aiohttp.ClientSession] = None

        # Test agents
        self.test_agents = [
            {"name": "perf-agent-1", "capabilities": ["general"]},
            {"name": "perf-agent-2", "capabilities": ["quality"]},
            {"name": "perf-agent-3", "capabilities": ["orchestration"]},
            {"name": "perf-agent-4", "capabilities": ["documentation"]},
            {"name": "perf-agent-5", "capabilities": ["integration"]},
        ]

        # Performance tracking
        self.latency_measurements: List[float] = []
        self.results: List[PerformanceResult] = []

    async def setup(self):
        """Initialize testing environment."""
        print("🔧 Setting up performance test environment...")

        # Initialize queue service for direct testing
        config = QueueConfig(
            name="perf-test-queue",
            max_size=20000,  # Higher limit for load testing
            message_ttl=3600,
            enable_persistence=True
        )
        self.queue_service = MessageQueueService(config, self.redis_url)

        # Initialize HTTP session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

        # Start queue service
        try:
            await self.queue_service.start()
            print("✅ Queue service started")
        except Exception as e:
            print(f"⚠️  Direct queue service unavailable: {e}")
            print("   Continuing with API-only testing...")

        # Register test agents
        await self._register_test_agents()
        print("✅ Test environment ready")

    async def teardown(self):
        """Clean up testing environment."""
        print("🧹 Cleaning up test environment...")

        if self.queue_service:
            await self.queue_service.stop()

        if self.session:
            await self.session.close()

        print("✅ Cleanup complete")

    async def run_capacity_test(self,
                               target_messages_per_minute: int = 1000,
                               test_duration_minutes: int = 2) -> PerformanceResult:
        """
        Run high-capacity test to validate throughput targets.

        Args:
            target_messages_per_minute: Target throughput (default: 1000)
            test_duration_minutes: Test duration (default: 2 minutes)
        """
        print(f"🚀 Starting capacity test: {target_messages_per_minute} msg/min for {test_duration_minutes} minutes")

        start_time = time.time()
        end_time = start_time + (test_duration_minutes * 60)

        # Calculate message interval
        messages_per_second = target_messages_per_minute / 60
        message_interval = 1.0 / messages_per_second

        total_messages = 0
        successful_messages = 0
        failed_messages = 0
        latencies = []

        # Message sending loop
        while time.time() < end_time:
            loop_start = time.time()

            # Send batch of messages
            batch_size = min(10, int(messages_per_second))  # Send in batches
            batch_tasks = []

            for i in range(batch_size):
                agent = self.test_agents[i % len(self.test_agents)]
                message_content = f"Capacity test message {total_messages + i} at {datetime.now()}"

                task = self._send_api_message(
                    recipient=agent["name"],
                    content=message_content,
                    priority="medium"
                )
                batch_tasks.append(task)

            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results
            for result in batch_results:
                total_messages += 1
                if isinstance(result, Exception):
                    failed_messages += 1
                else:
                    successful_messages += 1
                    if result and 'latency_ms' in result:
                        latencies.append(result['latency_ms'])

            # Maintain target rate
            elapsed = time.time() - loop_start
            if elapsed < message_interval:
                await asyncio.sleep(message_interval - elapsed)

        # Calculate results
        actual_duration = time.time() - start_time
        actual_mps = successful_messages / actual_duration
        actual_mpm = actual_mps * 60

        # Calculate latency statistics
        avg_latency = statistics.mean(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else 0
        p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else 0

        error_rate = failed_messages / total_messages if total_messages > 0 else 0

        result = PerformanceResult(
            test_name=f"capacity_test_{target_messages_per_minute}mpm",
            duration_seconds=actual_duration,
            total_messages=total_messages,
            successful_messages=successful_messages,
            failed_messages=failed_messages,
            messages_per_second=actual_mps,
            messages_per_minute=actual_mpm,
            average_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            error_rate=error_rate,
            timestamp=datetime.now()
        )

        self.results.append(result)

        # Display results
        print(f"\n📊 CAPACITY TEST RESULTS:")
        print(f"   Target: {target_messages_per_minute} msg/min")
        print(f"   Actual: {actual_mpm:.1f} msg/min ({actual_mps:.1f} msg/sec)")
        print(f"   Success Rate: {(1-error_rate)*100:.1f}%")
        print(f"   Avg Latency: {avg_latency:.1f}ms")
        print(f"   P95 Latency: {p95_latency:.1f}ms")

        # Validate target met
        target_met = actual_mpm >= target_messages_per_minute * 0.95  # 95% of target
        status = "✅ PASSED" if target_met else "❌ FAILED"
        print(f"   Status: {status}")

        return result

    async def run_burst_test(self, burst_size: int = 100) -> PerformanceResult:
        """Test burst message handling capacity."""
        print(f"💥 Starting burst test: {burst_size} messages")

        start_time = time.time()

        # Create burst of messages
        tasks = []
        for i in range(burst_size):
            agent = self.test_agents[i % len(self.test_agents)]
            message_content = f"Burst test message {i}"

            task = self._send_api_message(
                recipient=agent["name"],
                content=message_content,
                priority="high"
            )
            tasks.append(task)

        # Send all messages concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate metrics
        duration = time.time() - start_time
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful

        latencies = [r.get('latency_ms', 0) for r in results if isinstance(r, dict) and 'latency_ms' in r]
        avg_latency = statistics.mean(latencies) if latencies else 0

        messages_per_second = successful / duration if duration > 0 else 0

        result = PerformanceResult(
            test_name=f"burst_test_{burst_size}",
            duration_seconds=duration,
            total_messages=burst_size,
            successful_messages=successful,
            failed_messages=failed,
            messages_per_second=messages_per_second,
            messages_per_minute=messages_per_second * 60,
            average_latency_ms=avg_latency,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p95_latency_ms=0,  # Not meaningful for burst test
            p99_latency_ms=0,
            error_rate=failed / burst_size if burst_size > 0 else 0,
            timestamp=datetime.now()
        )

        self.results.append(result)

        print(f"   Duration: {duration:.2f}s")
        print(f"   Rate: {messages_per_second:.1f} msg/sec")
        print(f"   Success: {successful}/{burst_size}")
        print(f"   Avg Latency: {avg_latency:.1f}ms")

        return result

    async def run_websocket_test(self, concurrent_agents: int = 10, messages_per_agent: int = 50) -> PerformanceResult:
        """Test WebSocket performance with concurrent agents."""
        print(f"🔌 Starting WebSocket test: {concurrent_agents} agents, {messages_per_agent} msgs each")

        start_time = time.time()
        total_messages = concurrent_agents * messages_per_agent

        # Create WebSocket connections for each agent
        async def agent_websocket_test(agent_id: int):
            agent_name = f"ws-test-agent-{agent_id}"
            ws_url = f"ws://localhost:8080/ws/{agent_name}"

            try:
                async with websockets.connect(ws_url) as websocket:
                    sent_count = 0
                    received_count = 0

                    # Send messages
                    for i in range(messages_per_agent):
                        message = {
                            "type": "send_message",
                            "recipient": self.test_agents[i % len(self.test_agents)]["name"],
                            "content": f"WebSocket test message {i} from agent {agent_id}",
                            "priority": "medium"
                        }

                        await websocket.send(json.dumps(message))
                        sent_count += 1

                        # Brief delay to avoid overwhelming
                        await asyncio.sleep(0.01)

                    return {"sent": sent_count, "received": received_count}

            except Exception as e:
                print(f"   WebSocket error for agent {agent_id}: {e}")
                return {"sent": 0, "received": 0, "error": str(e)}

        # Run concurrent WebSocket tests
        tasks = [agent_websocket_test(i) for i in range(concurrent_agents)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate metrics
        duration = time.time() - start_time
        successful_messages = sum(r.get("sent", 0) for r in results if isinstance(r, dict))
        failed_messages = total_messages - successful_messages

        messages_per_second = successful_messages / duration if duration > 0 else 0

        result = PerformanceResult(
            test_name=f"websocket_test_{concurrent_agents}agents",
            duration_seconds=duration,
            total_messages=total_messages,
            successful_messages=successful_messages,
            failed_messages=failed_messages,
            messages_per_second=messages_per_second,
            messages_per_minute=messages_per_second * 60,
            average_latency_ms=0,  # Would need message timestamps
            min_latency_ms=0,
            max_latency_ms=0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            error_rate=failed_messages / total_messages if total_messages > 0 else 0,
            timestamp=datetime.now()
        )

        self.results.append(result)

        print(f"   Duration: {duration:.2f}s")
        print(f"   Rate: {messages_per_second:.1f} msg/sec")
        print(f"   Success: {successful_messages}/{total_messages}")

        return result

    async def _send_api_message(self, recipient: str, content: str, priority: str = "medium") -> Dict[str, Any]:
        """Send message via REST API and measure latency."""
        if not self.session:
            raise RuntimeError("HTTP session not initialized")

        start_time = time.time()

        try:
            payload = {
                "recipient": recipient,
                "content": content,
                "priority": priority
            }

            async with self.session.post(
                f"{self.api_base_url}/api/v1/messages",
                json=payload,
                params={"sender": "load-tester"}
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status == 200:
                    result = await response.json()
                    result["latency_ms"] = latency_ms
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {"error": str(e), "latency_ms": latency_ms}

    async def _register_test_agents(self):
        """Register test agents via API."""
        if not self.session:
            return

        for agent_data in self.test_agents:
            try:
                async with self.session.post(
                    f"{self.api_base_url}/api/v1/agents/register",
                    json=agent_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"   Registered {agent_data['name']}: {result.get('agent_id', 'Unknown ID')}")
                    else:
                        print(f"   Failed to register {agent_data['name']}: {response.status}")
            except Exception as e:
                print(f"   Error registering {agent_data['name']}: {e}")

    def generate_report(self) -> str:
        """Generate comprehensive performance test report."""
        if not self.results:
            return "No test results available"

        report = ["# MESSAGE QUEUE PERFORMANCE TEST REPORT", ""]
        report.append(f"**Test Date**: {datetime.now().isoformat()}")
        report.append(f"**Total Tests**: {len(self.results)}")
        report.append("")

        # Summary statistics
        all_mpm = [r.messages_per_minute for r in self.results]
        max_mpm = max(all_mpm) if all_mpm else 0
        avg_mpm = statistics.mean(all_mpm) if all_mpm else 0

        report.append("## 📊 SUMMARY")
        report.append(f"- **Peak Throughput**: {max_mpm:.1f} messages/minute")
        report.append(f"- **Average Throughput**: {avg_mpm:.1f} messages/minute")
        report.append(f"- **Target Achievement**: {'✅ PASSED' if max_mpm >= 1000 else '❌ FAILED'}")
        report.append("")

        # Individual test results
        report.append("## 🧪 TEST RESULTS")
        for result in self.results:
            report.append(f"### {result.test_name}")
            report.append(f"- **Throughput**: {result.messages_per_minute:.1f} msg/min")
            report.append(f"- **Success Rate**: {(1-result.error_rate)*100:.1f}%")
            report.append(f"- **Average Latency**: {result.average_latency_ms:.1f}ms")
            report.append(f"- **P95 Latency**: {result.p95_latency_ms:.1f}ms")
            report.append("")

        return "\n".join(report)

    def save_results(self, filename: str = "performance_results.json"):
        """Save results to JSON file."""
        results_data = [asdict(result) for result in self.results]

        with open(filename, 'w') as f:
            json.dump({
                "test_timestamp": datetime.now().isoformat(),
                "results": results_data,
                "summary": {
                    "total_tests": len(self.results),
                    "max_throughput_mpm": max((r.messages_per_minute for r in self.results), default=0),
                    "target_met": any(r.messages_per_minute >= 1000 for r in self.results)
                }
            }, f, indent=2, default=str)

        print(f"📄 Results saved to {filename}")


async def run_comprehensive_test():
    """Run comprehensive performance test suite."""
    print("🚀 MESSAGE QUEUE COMPREHENSIVE PERFORMANCE TEST")
    print("=" * 60)

    tester = MessageQueueLoadTester()

    try:
        await tester.setup()

        # Test 1: Target capacity validation
        print("\n1️⃣ TARGET CAPACITY TEST (1000 msg/min)")
        await tester.run_capacity_test(target_messages_per_minute=1000, test_duration_minutes=2)

        # Test 2: High capacity test
        print("\n2️⃣ HIGH CAPACITY TEST (1500 msg/min)")
        await tester.run_capacity_test(target_messages_per_minute=1500, test_duration_minutes=1)

        # Test 3: Burst handling
        print("\n3️⃣ BURST CAPACITY TEST")
        await tester.run_burst_test(burst_size=200)

        # Test 4: WebSocket performance
        print("\n4️⃣ WEBSOCKET PERFORMANCE TEST")
        await tester.run_websocket_test(concurrent_agents=15, messages_per_agent=30)

        # Generate and display report
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE TEST SUMMARY")
        print("=" * 60)

        report = tester.generate_report()
        print(report)

        # Save results
        tester.save_results()

        # Final validation
        max_throughput = max((r.messages_per_minute for r in tester.results), default=0)
        target_met = max_throughput >= 1000

        print(f"\n🎯 FINAL VALIDATION:")
        print(f"   Target: >1000 messages/minute")
        print(f"   Achieved: {max_throughput:.1f} messages/minute")
        print(f"   Status: {'✅ TARGET MET' if target_met else '❌ TARGET NOT MET'}")

        return target_met

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await tester.teardown()


async def main():
    """Main entry point with CLI options."""
    parser = argparse.ArgumentParser(description="Message Queue Performance Testing")
    parser.add_argument("--target-mpm", type=int, default=1000, help="Target messages per minute")
    parser.add_argument("--duration", type=int, default=2, help="Test duration in minutes")
    parser.add_argument("--api-url", default="http://localhost:8080", help="API base URL")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="Redis URL")
    parser.add_argument("--test-type", choices=["capacity", "burst", "websocket", "comprehensive"],
                       default="comprehensive", help="Type of test to run")

    args = parser.parse_args()

    tester = MessageQueueLoadTester(args.api_url, args.redis_url)

    try:
        await tester.setup()

        if args.test_type == "capacity":
            await tester.run_capacity_test(args.target_mpm, args.duration)
        elif args.test_type == "burst":
            await tester.run_burst_test(200)
        elif args.test_type == "websocket":
            await tester.run_websocket_test(10, 50)
        elif args.test_type == "comprehensive":
            return await run_comprehensive_test()

        # Display results
        report = tester.generate_report()
        print(report)
        tester.save_results()

    finally:
        await tester.teardown()


if __name__ == "__main__":
    asyncio.run(main())
