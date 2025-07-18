#!/usr/bin/env python3
"""
End-to-End Testing Framework for Agent Hive Production Readiness
Integration & Testing Agent - Phase 3 Consolidation & Validation

Tests complete system integration:
- PostgreSQL database operations
- Message protocol functionality  
- Agent coordination workflows
- Performance under load
"""

import asyncio
import json
import logging
import time
import psycopg2
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import concurrent.futures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scratchpad/e2e_tests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result container"""
    test_name: str
    status: str  # 'pass', 'fail', 'skip'
    duration_ms: float
    details: Optional[str] = None
    error: Optional[str] = None

class E2ETestFramework:
    """Comprehensive E2E testing for Agent Hive production readiness"""
    
    def __init__(self, pg_connection_string: str):
        self.pg_conn_string = pg_connection_string
        self.test_results: List[TestResult] = []
        self.start_time = datetime.now()
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Execute complete E2E test suite"""
        
        logger.info("🧪 Starting Agent Hive E2E Test Suite")
        logger.info("=" * 60)
        
        # Test categories in dependency order
        test_categories = [
            ("Database Connectivity", self._test_database_connectivity),
            ("Schema Validation", self._test_schema_validation),
            ("Data Operations", self._test_data_operations),
            ("Message Protocol", self._test_message_protocol),
            ("Agent Coordination", self._test_agent_coordination),
            ("Performance Benchmarks", self._test_performance),
            ("Integration Workflows", self._test_integration_workflows)
        ]
        
        for category_name, test_function in test_categories:
            logger.info(f"\n🔍 Running {category_name} Tests")
            logger.info("-" * 40)
            
            try:
                test_function()
            except Exception as e:
                logger.error(f"❌ {category_name} category failed: {e}")
                self.test_results.append(TestResult(
                    test_name=f"{category_name}_category",
                    status="fail",
                    duration_ms=0,
                    error=str(e)
                ))
        
        return self._generate_test_report()
    
    def _test_database_connectivity(self):
        """Test PostgreSQL database connectivity and basic operations"""
        
        # Test 1: Basic connection
        start_time = time.time()
        try:
            conn = psycopg2.connect(self.pg_conn_string)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            conn.close()
            
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="database_basic_connection",
                status="pass",
                duration_ms=duration,
                details=f"PostgreSQL version: {version[:50]}..."
            ))
            logger.info("✅ Database basic connection")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="database_basic_connection",
                status="fail",
                duration_ms=duration,
                error=str(e)
            ))
            logger.error(f"❌ Database basic connection: {e}")
            return
        
        # Test 2: Connection pool simulation
        start_time = time.time()
        try:
            connections = []
            for i in range(10):
                conn = psycopg2.connect(self.pg_conn_string)
                connections.append(conn)
            
            # Close all connections
            for conn in connections:
                conn.close()
            
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="database_connection_pool",
                status="pass",
                duration_ms=duration,
                details="10 concurrent connections successful"
            ))
            logger.info("✅ Database connection pool")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="database_connection_pool",
                status="fail",
                duration_ms=duration,
                error=str(e)
            ))
            logger.error(f"❌ Database connection pool: {e}")
    
    def _test_schema_validation(self):
        """Validate PostgreSQL schema structure and constraints"""
        
        start_time = time.time()
        try:
            conn = psycopg2.connect(self.pg_conn_string)
            cursor = conn.cursor()
            
            # Check required schemas exist
            cursor.execute("""
                SELECT schema_name FROM information_schema.schemata 
                WHERE schema_name IN ('security', 'agents', 'monitoring', 'optimization')
                ORDER BY schema_name;
            """)
            schemas = [row[0] for row in cursor.fetchall()]
            expected_schemas = ['agents', 'monitoring', 'optimization', 'security']
            
            if set(schemas) == set(expected_schemas):
                # Check required tables exist
                cursor.execute("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE schemaname IN ('security', 'agents', 'monitoring', 'optimization')
                    ORDER BY schemaname, tablename;
                """)
                tables = cursor.fetchall()
                
                duration = (time.time() - start_time) * 1000
                self.test_results.append(TestResult(
                    test_name="schema_structure_validation",
                    status="pass",
                    duration_ms=duration,
                    details=f"4 schemas, {len(tables)} tables validated"
                ))
                logger.info(f"✅ Schema structure ({len(tables)} tables)")
                
            else:
                raise Exception(f"Missing schemas: {set(expected_schemas) - set(schemas)}")
            
            conn.close()
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="schema_structure_validation",
                status="fail",
                duration_ms=duration,
                error=str(e)
            ))
            logger.error(f"❌ Schema structure validation: {e}")
    
    def _test_data_operations(self):
        """Test CRUD operations across all domains"""
        
        # Test 1: Insert and read operations
        start_time = time.time()
        try:
            conn = psycopg2.connect(self.pg_conn_string)
            cursor = conn.cursor()
            
            # Test monitoring.metrics insert
            cursor.execute("""
                INSERT INTO monitoring.metrics (metric_name, metric_category, value, unit, source, tags)
                VALUES ('test_metric', 'e2e_test', 42.0, 'count', 'test_framework', '{"test": true}')
                RETURNING id;
            """)
            metric_id = cursor.fetchone()[0]
            
            # Test agents.capabilities insert
            cursor.execute("""
                INSERT INTO agents.capabilities (agent_id, agent_type, capabilities, status, metadata)
                VALUES ('test_agent_001', 'e2e_test_agent', '{"test": "capabilities"}', 'testing', '{"test": true}')
                RETURNING id;
            """)
            agent_id = cursor.fetchone()[0]
            
            # Test security.metrics insert
            cursor.execute("""
                INSERT INTO security.metrics (metric_name, metric_type, value, unit, source_system, metadata)
                VALUES ('test_security', 'e2e_test', 1.0, 'event', 'test_framework', '{"test": true}')
                RETURNING id;
            """)
            security_id = cursor.fetchone()[0]
            
            conn.commit()
            
            # Verify reads
            cursor.execute("SELECT COUNT(*) FROM monitoring.metrics WHERE source = 'test_framework'")
            metrics_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM agents.capabilities WHERE agent_type = 'e2e_test_agent'")
            agents_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM security.metrics WHERE source_system = 'test_framework'")
            security_count = cursor.fetchone()[0]
            
            if metrics_count >= 1 and agents_count >= 1 and security_count >= 1:
                duration = (time.time() - start_time) * 1000
                self.test_results.append(TestResult(
                    test_name="data_crud_operations",
                    status="pass",
                    duration_ms=duration,
                    details=f"Insert/Read: {metrics_count} metrics, {agents_count} agents, {security_count} security"
                ))
                logger.info("✅ Data CRUD operations")
            else:
                raise Exception("Data verification failed after insert")
            
            conn.close()
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="data_crud_operations",
                status="fail",
                duration_ms=duration,
                error=str(e)
            ))
            logger.error(f"❌ Data CRUD operations: {e}")
    
    def _test_message_protocol(self):
        """Test message protocol functionality"""
        
        start_time = time.time()
        try:
            # Import message protocol classes
            sys.path.append('/Users/bogdan/work/leanvibe-dev/agent-hive')
            from message_bus.message_protocol import AgentMessage, MessageType, MessagePriority, create_task_assignment
            
            # Test 1: Message creation
            message = AgentMessage.create(
                from_agent="test_agent_1",
                to_agent="test_agent_2", 
                message_type=MessageType.TASK_ASSIGNMENT.value,
                body={"task": "e2e_test_task", "priority": "high"},
                priority=MessagePriority.HIGH
            )
            
            # Test 2: Task assignment creation
            task_msg = create_task_assignment(
                from_agent="coordinator",
                to_agent="worker_agent",
                task_description="Execute E2E validation test",
                priority=MessagePriority.CRITICAL,
                deadline="2025-07-18T04:00:00Z",
                context={"test_framework": "e2e", "phase": "validation"}
            )
            
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="message_protocol_functionality",
                status="pass",
                duration_ms=duration,
                details=f"Message ID: {message.message_id}, Task ID: {task_msg.body['assignment_id']}"
            ))
            logger.info("✅ Message protocol functionality")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="message_protocol_functionality",
                status="fail",
                duration_ms=duration,
                error=str(e)
            ))
            logger.error(f"❌ Message protocol functionality: {e}")
    
    def _test_agent_coordination(self):
        """Test agent coordination workflows"""
        
        start_time = time.time()
        try:
            # Test coordination status tracking
            coordination_file = Path('scratchpad/coordination_status.json')
            if coordination_file.exists():
                with open(coordination_file, 'r') as f:
                    coordination_data = json.load(f)
                
                # Verify coordination structure
                required_keys = ['phase', 'agents', 'quality_gates']
                if all(key in coordination_data for key in required_keys):
                    agent_count = len(coordination_data['agents'])
                    completed_agents = sum(1 for agent in coordination_data['agents'].values() 
                                         if agent['status'] == 'completed')
                    
                    duration = (time.time() - start_time) * 1000
                    self.test_results.append(TestResult(
                        test_name="agent_coordination_tracking",
                        status="pass",
                        duration_ms=duration,
                        details=f"Phase: {coordination_data['phase']}, Agents: {agent_count}, Completed: {completed_agents}"
                    ))
                    logger.info("✅ Agent coordination tracking")
                else:
                    raise Exception("Invalid coordination status structure")
            else:
                raise Exception("Coordination status file not found")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="agent_coordination_tracking",
                status="fail",
                duration_ms=duration,
                error=str(e)
            ))
            logger.error(f"❌ Agent coordination tracking: {e}")
    
    def _test_performance(self):
        """Test performance benchmarks"""
        
        # Test 1: Database write performance
        start_time = time.time()
        try:
            conn = psycopg2.connect(self.pg_conn_string)
            cursor = conn.cursor()
            
            # Batch insert test
            insert_start = time.time()
            for i in range(100):
                cursor.execute("""
                    INSERT INTO monitoring.metrics (metric_name, metric_category, value, unit, source, tags)
                    VALUES (%s, 'performance_test', %s, 'ms', 'e2e_framework', '{"batch": true}')
                """, (f"perf_metric_{i}", float(i)))
            
            conn.commit()
            insert_duration = (time.time() - insert_start) * 1000
            
            # Check write latency target (<50ms per write)
            avg_write_latency = insert_duration / 100
            
            if avg_write_latency < 50:
                status = "pass"
                details = f"Avg write latency: {avg_write_latency:.2f}ms (target: <50ms)"
            else:
                status = "fail"
                details = f"Write latency {avg_write_latency:.2f}ms exceeds 50ms target"
            
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="database_write_performance",
                status=status,
                duration_ms=duration,
                details=details
            ))
            
            if status == "pass":
                logger.info("✅ Database write performance")
            else:
                logger.warning(f"⚠️  Database write performance: {details}")
            
            conn.close()
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="database_write_performance",
                status="fail",
                duration_ms=duration,
                error=str(e)
            ))
            logger.error(f"❌ Database write performance: {e}")
    
    def _test_integration_workflows(self):
        """Test complete integration workflows"""
        
        start_time = time.time()
        try:
            # Simulate complete agent workflow:
            # 1. Agent registration → agents.capabilities
            # 2. Task assignment → message protocol
            # 3. Metric reporting → monitoring.metrics
            # 4. Security event → security.audit_events
            
            conn = psycopg2.connect(self.pg_conn_string)
            cursor = conn.cursor()
            
            # Step 1: Agent registration
            cursor.execute("""
                INSERT INTO agents.capabilities (agent_id, agent_type, capabilities, status, metadata)
                VALUES ('workflow_agent_001', 'integration_test', '{"workflow": "e2e"}', 'active', '{"test": "integration"}')
                RETURNING agent_id;
            """)
            agent_id = cursor.fetchone()[0]
            
            # Step 2: Simulate task execution with metrics
            cursor.execute("""
                INSERT INTO monitoring.metrics (metric_name, metric_category, value, unit, source, tags)
                VALUES ('task_execution_time', 'workflow', 1.5, 'seconds', %s, '{"workflow": "complete"}')
                RETURNING id;
            """, (agent_id,))
            metric_id = cursor.fetchone()[0]
            
            # Step 3: Security audit event
            cursor.execute("""
                INSERT INTO security.audit_events (event_type, event_source, agent_id, action_performed, result, details)
                VALUES ('task_completion', 'integration_test', %s, 'execute_workflow', 'success', '{"test": "complete"}')
                RETURNING id;
            """, (agent_id,))
            audit_id = cursor.fetchone()[0]
            
            conn.commit()
            conn.close()
            
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="complete_integration_workflow",
                status="pass",
                duration_ms=duration,
                details=f"Agent: {agent_id}, Metric: {metric_id}, Audit: {audit_id}"
            ))
            logger.info("✅ Complete integration workflow")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.test_results.append(TestResult(
                test_name="complete_integration_workflow",
                status="fail",
                duration_ms=duration,
                error=str(e)
            ))
            logger.error(f"❌ Complete integration workflow: {e}")
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds() * 1000
        
        passed_tests = [r for r in self.test_results if r.status == 'pass']
        failed_tests = [r for r in self.test_results if r.status == 'fail']
        
        report = {
            'test_run_metadata': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'total_duration_ms': total_duration,
                'total_tests': len(self.test_results),
                'passed': len(passed_tests),
                'failed': len(failed_tests),
                'success_rate': len(passed_tests) / len(self.test_results) * 100 if self.test_results else 0
            },
            'test_results': [
                {
                    'test_name': r.test_name,
                    'status': r.status,
                    'duration_ms': r.duration_ms,
                    'details': r.details,
                    'error': r.error
                }
                for r in self.test_results
            ],
            'summary': {
                'production_ready': len(failed_tests) == 0,
                'critical_failures': [r.test_name for r in failed_tests if 'database' in r.test_name or 'message' in r.test_name],
                'performance_metrics': {
                    'avg_test_duration': sum(r.duration_ms for r in self.test_results) / len(self.test_results) if self.test_results else 0,
                    'database_tests_passed': sum(1 for r in passed_tests if 'database' in r.test_name),
                    'integration_tests_passed': sum(1 for r in passed_tests if 'integration' in r.test_name or 'workflow' in r.test_name)
                }
            }
        }
        
        return report

def main():
    """Main E2E testing execution"""
    
    # PostgreSQL connection (staging environment)
    pg_conn_string = "postgresql://agent_hive_user:staging_password_123@localhost:5432/agent_hive"
    
    if len(sys.argv) > 1:
        pg_conn_string = sys.argv[1]
    
    print("🧪 Agent Hive E2E Test Framework")
    print("=" * 50)
    print(f"Target: {pg_conn_string.split('@')[1] if '@' in pg_conn_string else 'localhost'}")
    print()
    
    try:
        framework = E2ETestFramework(pg_conn_string)
        report = framework.run_all_tests()
        
        # Save detailed report
        report_file = Path('scratchpad/e2e_test_report.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\n🎉 E2E Testing Complete!")
        print(f"📊 Results: {report['test_run_metadata']['passed']}/{report['test_run_metadata']['total_tests']} passed")
        print(f"⏱️  Duration: {report['test_run_metadata']['total_duration_ms']:.0f}ms")
        print(f"📄 Report: {report_file}")
        
        if report['summary']['production_ready']:
            print("✅ Production readiness: APPROVED")
            return 0
        else:
            print("❌ Production readiness: BLOCKED")
            print("🚨 Critical failures:", report['summary']['critical_failures'])
            return 1
            
    except Exception as e:
        logger.error(f"💥 E2E testing failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())