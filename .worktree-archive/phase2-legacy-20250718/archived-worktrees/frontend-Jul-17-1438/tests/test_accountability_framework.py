#!/usr/bin/env python3
"""
Tests for Accountability Framework - XP Methodology Compliance
Test-Driven Development requirement for XP quality gate.
"""

import pytest
import tempfile
import json
from pathlib import Path

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.accountability_framework import (
    AccountabilityFramework,
    TaskStatus,
    EscalationLevel,
    EvidenceRequirement
)


class TestAccountabilityFramework:
    """Test suite for AccountabilityFramework - XP TDD compliance."""
    
    @pytest.fixture
    def framework(self):
        """Create accountability framework instance for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "default_deadline_hours": 2,
                "checkpoint_intervals": [0.5, 1.0],
                "escalation_thresholds": {
                    "warning": 0.75,
                    "critical": 0.9,
                    "urgent": 1.0,
                    "emergency": 1.25
                },
                "max_reassignments": 1,
                "evidence_validation_timeout": 5
            }
            json.dump(config, f)
            config_path = f.name
        
        framework = AccountabilityFramework(config_path)
        yield framework
        
        # Cleanup
        Path(config_path).unlink(missing_ok=True)
    
    def test_framework_initialization(self, framework):
        """Test framework initialization - XP Simple Design."""
        assert framework.config["default_deadline_hours"] == 2
        assert len(framework.evidence_types) > 0
        assert not framework.monitoring_active
        assert framework.tasks == {}
    
    @pytest.mark.asyncio
    async def test_task_assignment(self, framework):
        """Test task assignment functionality - XP Small Releases."""
        task_id = await framework.assign_task(
            agent_id="test-agent",
            task_description="Test task implementation",
            deadline_hours=1,
            priority="high"
        )
        
        assert task_id.startswith("task_")
        assert task_id in framework.tasks
        
        task = framework.tasks[task_id]
        assert task.agent_id == "test-agent"
        assert task.task_description == "Test task implementation"
        assert task.priority == "high"
        assert task.status == TaskStatus.ASSIGNED
    
    @pytest.mark.asyncio
    async def test_task_progress_update(self, framework):
        """Test task progress updates - XP Continuous Integration."""
        task_id = await framework.assign_task(
            agent_id="test-agent",
            task_description="Test progress tracking"
        )
        
        # Update task status
        result = await framework.update_task_progress(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            evidence=["git commit abc123"]
        )
        
        assert result is True
        task = framework.tasks[task_id]
        assert task.status == TaskStatus.IN_PROGRESS
        assert "git commit abc123" in task.evidence_collected
    
    def test_evidence_requirements(self, framework):
        """Test evidence requirement definitions - XP Test-Driven Development."""
        evidence_types = framework.evidence_types
        
        # Verify required evidence types exist
        assert "git_commit" in evidence_types
        assert "tests_passing" in evidence_types
        assert "quality_gates" in evidence_types
        
        # Verify evidence structure
        git_evidence = evidence_types["git_commit"]
        assert git_evidence.type == "git_commit"
        assert git_evidence.required is True
        assert git_evidence.validation_command is not None
    
    def test_get_task_status(self, framework):
        """Test task status retrieval - XP Collective Code Ownership."""
        # Test non-existent task
        status = framework.get_task_status("non-existent")
        assert status is None
        
        # This test verifies the basic structure without async complexity
        assert hasattr(framework, 'get_task_status')
        assert callable(framework.get_task_status)
    
    @pytest.mark.asyncio
    async def test_escalation_levels(self, framework):
        """Test escalation level definitions - XP Sustainable Pace."""
        # Test escalation enum values
        assert EscalationLevel.WARNING.value == "warning"
        assert EscalationLevel.CRITICAL.value == "critical"
        assert EscalationLevel.URGENT.value == "urgent"
        assert EscalationLevel.EMERGENCY.value == "emergency"
        
        # Test escalation is properly initialized
        task_id = await framework.assign_task(
            agent_id="test-agent",
            task_description="Test escalation"
        )
        
        task = framework.tasks[task_id]
        assert task.escalation_level == EscalationLevel.WARNING
    
    def test_task_status_enum(self):
        """Test task status enumeration - XP Simple Design."""
        assert TaskStatus.ASSIGNED.value == "assigned"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.OVERDUE.value == "overdue"
        assert TaskStatus.REASSIGNED.value == "reassigned"
    
    @pytest.mark.asyncio
    async def test_accountability_report_generation(self, framework):
        """Test accountability report generation - XP Metrics Collection."""
        # Generate report for empty system
        report = await framework.generate_accountability_report()
        
        assert "generated_at" in report
        assert "summary" in report
        assert "tasks" in report
        
        summary = report["summary"]
        assert summary["total_tasks"] == 0
        assert summary["completed_tasks"] == 0
        assert summary["completion_rate"] == 0
    
    def test_evidence_requirement_dataclass(self):
        """Test evidence requirement data structure - XP Simple Design."""
        evidence = EvidenceRequirement(
            type="test_type",
            description="Test description",
            validation_command="test command",
            required=True
        )
        
        assert evidence.type == "test_type"
        assert evidence.description == "Test description"
        assert evidence.validation_command == "test command"
        assert evidence.required is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])