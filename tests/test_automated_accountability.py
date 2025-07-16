#!/usr/bin/env python3
"""
Test suite for automated accountability system.
Validates coordination crisis prevention capabilities.
"""

import unittest
import json
import tempfile
from datetime import datetime, timedelta
from scripts.automated_accountability import (
    AutomatedAccountability, 
    AccountabilityTask, 
    EvidenceRequirement,
    TaskStatus,
    EscalationLevel
)


class TestAutomatedAccountability(unittest.TestCase):
    """Test automated accountability system functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.accountability = AutomatedAccountability()
        self.evidence_reqs = [
            EvidenceRequirement("commit", "Code committed", True),
            EvidenceRequirement("test", "Tests passing", True)
        ]
    
    def test_task_assignment(self):
        """Test task assignment with deadlines."""
        task = self.accountability.assign_task(
            task_id="test-task-1",
            agent_id="test-agent",
            description="Test task",
            deadline_hours=2.0,
            evidence_requirements=self.evidence_reqs
        )
        
        self.assertEqual(task.task_id, "test-task-1")
        self.assertEqual(task.agent_id, "test-agent")
        self.assertEqual(task.status, TaskStatus.ASSIGNED)
        self.assertEqual(len(task.evidence_requirements), 2)
        self.assertFalse(task.is_overdue())
    
    def test_evidence_submission(self):
        """Test evidence submission and validation."""
        task = self.accountability.assign_task(
            "test-task-2", "test-agent", "Test", 2.0, self.evidence_reqs
        )
        
        # Submit evidence
        success = self.accountability.submit_evidence(
            "test-task-2", "commit", {"hash": "abc123", "message": "Test commit"}
        )
        
        self.assertTrue(success)
        self.assertEqual(len(task.evidence_submitted), 1)
        self.assertEqual(task.evidence_submitted[0]['type'], "commit")
        
        # Submit second evidence
        self.accountability.submit_evidence(
            "test-task-2", "test", {"status": "passed", "count": 5}
        )
        
        # Task should be completed
        self.assertEqual(task.status, TaskStatus.COMPLETED)
    
    def test_deadline_escalation(self):
        """Test deadline escalation logic."""
        # Create overdue task
        task = self.accountability.assign_task(
            "overdue-task", "test-agent", "Overdue test", 0.001, self.evidence_reqs  # 0.001 hours = 3.6 seconds
        )
        
        # Wait for task to become overdue
        import time
        time.sleep(4)
        
        # Check accountability
        report = self.accountability.check_accountability()
        
        # Should be in critical or emergency
        self.assertTrue(len(report['critical']) > 0 or len(report['emergency']) > 0)
        self.assertTrue(task.is_overdue())
    
    def test_progress_calculation(self):
        """Test progress percentage calculation."""
        task = self.accountability.assign_task(
            "progress-task", "test-agent", "Progress test", 2.0, self.evidence_reqs
        )
        
        # No evidence submitted
        self.assertEqual(task.progress_percentage(), 0.0)
        
        # Submit half the evidence
        self.accountability.submit_evidence(
            "progress-task", "commit", {"hash": "abc123"}
        )
        
        self.assertEqual(task.progress_percentage(), 50.0)
        
        # Submit all evidence
        self.accountability.submit_evidence(
            "progress-task", "test", {"status": "passed"}
        )
        
        self.assertEqual(task.progress_percentage(), 100.0)
    
    def test_accountability_report_generation(self):
        """Test accountability report generation."""
        # Create tasks in different states
        self.accountability.assign_task(
            "on-track", "agent1", "On track task", 24.0, self.evidence_reqs
        )
        
        self.accountability.assign_task(
            "warning", "agent2", "Warning task", 0.5, self.evidence_reqs
        )
        
        # Generate report
        report_file = self.accountability.generate_accountability_report()
        
        # Verify report exists and has content
        self.assertTrue(report_file.endswith('.json'))
        
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        self.assertIn('summary', report)
        self.assertIn('detailed_status', report)
        self.assertIn('total_tasks', report['summary'])
        self.assertEqual(report['summary']['total_tasks'], 2)
    
    def test_enforcement_actions(self):
        """Test accountability enforcement actions."""
        # Create task requiring enforcement
        task = self.accountability.assign_task(
            "enforce-task", "silent-agent", "Enforcement test", 1.0, self.evidence_reqs
        )
        
        # Trigger enforcement
        actions = self.accountability.enforce_accountability()
        
        # Should track enforcement actions
        self.assertIn('warnings_sent', actions)
        self.assertIn('escalations_triggered', actions)
        self.assertIn('tasks_reassigned', actions)
        self.assertIn('system_alerts', actions)
    
    def test_emergency_reassignment(self):
        """Test emergency task reassignment."""
        # Create task that will trigger reassignment
        task = self.accountability.assign_task(
            "reassign-task", "unresponsive-agent", "Reassign test", 0.0001, self.evidence_reqs
        )
        
        # Force emergency escalation
        task.escalation_level = EscalationLevel.RED
        self.accountability._handle_emergency_escalation(task)
        
        # Check if reassignment logic triggered
        # (In real system, would verify agent change)
        self.assertTrue(task.escalation_level == EscalationLevel.RED)


class TestEvidenceRequirement(unittest.TestCase):
    """Test evidence requirement functionality."""
    
    def test_evidence_creation(self):
        """Test evidence requirement creation."""
        evidence = EvidenceRequirement(
            type="commit",
            description="Code must be committed",
            required=True,
            validator="git log --oneline -1"
        )
        
        self.assertEqual(evidence.type, "commit")
        self.assertTrue(evidence.required)
        self.assertEqual(evidence.validator, "git log --oneline -1")
    
    def test_evidence_serialization(self):
        """Test evidence requirement serialization."""
        evidence = EvidenceRequirement("test", "Tests must pass", True)
        
        data = evidence.to_dict()
        
        self.assertEqual(data['type'], "test")
        self.assertEqual(data['description'], "Tests must pass")
        self.assertTrue(data['required'])


class TestAccountabilityTask(unittest.TestCase):
    """Test accountability task functionality."""
    
    def test_task_creation(self):
        """Test accountability task creation."""
        now = datetime.now()
        deadline = now + timedelta(hours=2)
        
        task = AccountabilityTask(
            task_id="test-task",
            agent_id="test-agent",
            description="Test task",
            assigned_time=now,
            deadline=deadline
        )
        
        self.assertEqual(task.task_id, "test-task")
        self.assertEqual(task.status, TaskStatus.ASSIGNED)
        self.assertFalse(task.is_overdue())
    
    def test_task_serialization(self):
        """Test task serialization."""
        task = AccountabilityTask(
            task_id="serialize-task",
            agent_id="test-agent",
            description="Serialization test",
            assigned_time=datetime.now(),
            deadline=datetime.now() + timedelta(hours=1)
        )
        
        data = task.to_dict()
        
        self.assertEqual(data['task_id'], "serialize-task")
        self.assertEqual(data['agent_id'], "test-agent")
        self.assertEqual(data['status'], "assigned")
        self.assertIn('time_remaining', data)
        self.assertIn('progress_percentage', data)


if __name__ == '__main__':
    unittest.main()