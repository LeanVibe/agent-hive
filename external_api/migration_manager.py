"""
Migration Manager for Zero-Disruption Agent Transition
From tmux-based communication to message queue-based communication.

This module provides a seamless migration path that allows agents to operate
in dual-mode (both tmux and message queue) before fully transitioning.
"""

import asyncio
import json
import logging
import subprocess
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Callable
from concurrent.futures import ThreadPoolExecutor

from .models import ApiRequest, ApiResponse, EventPriority
from .event_streaming import EventStreaming

logger = logging.getLogger(__name__)


class AgentMigrationState(Enum):
    """States of agent migration process."""
    TMUX_ONLY = "tmux_only"
    DUAL_MODE = "dual_mode"
    MESSAGE_QUEUE_ONLY = "message_queue_only"
    MIGRATION_FAILED = "migration_failed"


class MigrationPhase(Enum):
    """Phases of the migration process."""
    DETECTION = "detection"
    PREPARATION = "preparation"
    DUAL_MODE_ACTIVATION = "dual_mode_activation"
    VALIDATION = "validation"
    CUTOVER = "cutover"
    CLEANUP = "cleanup"
    ROLLBACK = "rollback"


@dataclass
class AgentMigrationStatus:
    """Migration status for a specific agent."""
    agent_id: str
    current_state: AgentMigrationState
    migration_phase: MigrationPhase
    tmux_session: Optional[str] = None
    tmux_window: Optional[str] = None
    message_queue_endpoint: Optional[str] = None
    migration_started_at: Optional[datetime] = None
    last_tmux_activity: Optional[datetime] = None
    last_queue_activity: Optional[datetime] = None
    error_count: int = 0
    validation_results: Dict[str, Any] = field(default_factory=dict)
    rollback_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationConfig:
    """Configuration for migration process."""
    # Timeouts
    detection_timeout: int = 300  # 5 minutes
    dual_mode_duration: int = 1800  # 30 minutes
    validation_timeout: int = 600  # 10 minutes
    
    # Thresholds
    max_error_count: int = 3
    min_dual_mode_success_rate: float = 0.95
    
    # Validation settings
    validation_interval: int = 60  # seconds
    health_check_interval: int = 30  # seconds
    
    # Rollback settings
    auto_rollback_enabled: bool = True
    rollback_on_failure_rate: float = 0.8  # rollback if < 80% success
    
    # Communication settings
    tmux_session_name: str = "agent-hive"
    message_queue_base_url: str = "http://localhost:8080"


class MigrationManager:
    """
    Manages zero-disruption migration from tmux to message queue communication.
    
    Migration Strategy:
    1. Detection: Identify active tmux agents
    2. Preparation: Set up message queue endpoints
    3. Dual Mode: Run both tmux and message queue simultaneously
    4. Validation: Ensure message queue functionality
    5. Cutover: Switch to message queue only
    6. Cleanup: Remove tmux infrastructure
    """
    
    def __init__(self, config: MigrationConfig, event_streaming: EventStreaming):
        """
        Initialize migration manager.
        
        Args:
            config: Migration configuration
            event_streaming: Event streaming for message queue communication
        """
        self.config = config
        self.event_streaming = event_streaming
        self.agent_statuses: Dict[str, AgentMigrationStatus] = {}
        self.migration_active = False
        self.migration_id = None
        
        # Thread pool for tmux operations
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Migration callbacks
        self.phase_callbacks: Dict[MigrationPhase, List[Callable]] = {
            phase: [] for phase in MigrationPhase
        }
        
        logger.info("Migration Manager initialized")
    
    async def start_migration(self, agent_filter: Optional[List[str]] = None) -> str:
        """
        Start the migration process for all or specified agents.
        
        Args:
            agent_filter: Optional list of specific agent IDs to migrate
            
        Returns:
            Migration ID for tracking
        """
        if self.migration_active:
            raise RuntimeError("Migration already in progress")
        
        self.migration_id = f"migration_{uuid.uuid4().hex[:8]}"
        self.migration_active = True
        
        logger.info(f"Starting migration {self.migration_id}")
        
        try:
            # Phase 1: Detection
            await self._execute_phase(MigrationPhase.DETECTION, agent_filter)
            
            # Phase 2: Preparation
            await self._execute_phase(MigrationPhase.PREPARATION)
            
            # Phase 3: Dual Mode Activation
            await self._execute_phase(MigrationPhase.DUAL_MODE_ACTIVATION)
            
            # Phase 4: Validation (continuous during dual mode)
            await self._execute_phase(MigrationPhase.VALIDATION)
            
            # Phase 5: Cutover
            await self._execute_phase(MigrationPhase.CUTOVER)
            
            # Phase 6: Cleanup
            await self._execute_phase(MigrationPhase.CLEANUP)
            
            logger.info(f"Migration {self.migration_id} completed successfully")
            return self.migration_id
            
        except Exception as e:
            logger.error(f"Migration {self.migration_id} failed: {e}")
            await self._execute_phase(MigrationPhase.ROLLBACK)
            raise
        finally:
            self.migration_active = False
    
    async def _execute_phase(self, phase: MigrationPhase, agent_filter: Optional[List[str]] = None):
        """Execute a specific migration phase."""
        logger.info(f"Executing migration phase: {phase.value}")
        
        # Execute phase callbacks
        for callback in self.phase_callbacks[phase]:
            try:
                await callback(phase, self.agent_statuses)
            except Exception as e:
                logger.error(f"Phase callback failed: {e}")
        
        # Execute phase-specific logic
        if phase == MigrationPhase.DETECTION:
            await self._detect_tmux_agents(agent_filter)
        elif phase == MigrationPhase.PREPARATION:
            await self._prepare_message_queue_infrastructure()
        elif phase == MigrationPhase.DUAL_MODE_ACTIVATION:
            await self._activate_dual_mode()
        elif phase == MigrationPhase.VALIDATION:
            await self._validate_dual_mode_operation()
        elif phase == MigrationPhase.CUTOVER:
            await self._execute_cutover()
        elif phase == MigrationPhase.CLEANUP:
            await self._cleanup_tmux_infrastructure()
        elif phase == MigrationPhase.ROLLBACK:
            await self._execute_rollback()
    
    async def _detect_tmux_agents(self, agent_filter: Optional[List[str]] = None):
        """Detect active tmux agents."""
        logger.info("Detecting active tmux agents...")
        
        try:
            # Get tmux session information
            cmd = ["tmux", "list-windows", "-t", self.config.tmux_session_name, "-F", "#{window_name}"]
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, subprocess.run, cmd, 
                subprocess.PIPE, subprocess.PIPE, True
            )
            
            if result.returncode != 0:
                logger.warning(f"Failed to list tmux windows: {result.stderr}")
                return
            
            window_names = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Filter agent windows
            agent_windows = [
                name for name in window_names 
                if (name.startswith('agent-') or self._is_agent_window(name))
                and (not agent_filter or name in agent_filter or name.replace('agent-', '') in agent_filter)
            ]
            
            logger.info(f"Detected {len(agent_windows)} tmux agents: {agent_windows}")
            
            # Initialize migration status for each agent
            for window_name in agent_windows:
                agent_id = window_name.replace('agent-', '') if window_name.startswith('agent-') else window_name
                
                self.agent_statuses[agent_id] = AgentMigrationStatus(
                    agent_id=agent_id,
                    current_state=AgentMigrationState.TMUX_ONLY,
                    migration_phase=MigrationPhase.DETECTION,
                    tmux_session=self.config.tmux_session_name,
                    tmux_window=window_name,
                    migration_started_at=datetime.now()
                )
                
                # Check last activity
                await self._check_tmux_activity(agent_id)
            
        except Exception as e:
            logger.error(f"Agent detection failed: {e}")
            raise
    
    def _is_agent_window(self, window_name: str) -> bool:
        """Check if a window name represents an agent."""
        agent_patterns = [
            'integration-specialist',
            'service-mesh',
            'frontend',
            'security',
            'infrastructure',
            'performance',
            'monitoring',
            'pm-agent'
        ]
        return any(pattern in window_name for pattern in agent_patterns)
    
    async def _prepare_message_queue_infrastructure(self):
        """Prepare message queue infrastructure for agents."""
        logger.info("Preparing message queue infrastructure...")
        
        for agent_id, status in self.agent_statuses.items():
            try:
                # Create message queue endpoint for agent
                endpoint = f"/api/agents/{agent_id}/messages"
                status.message_queue_endpoint = endpoint
                
                # Register endpoint with event streaming
                await self.event_streaming.register_agent_endpoint(agent_id, endpoint)
                
                # Store rollback data
                status.rollback_data['original_tmux_window'] = status.tmux_window
                status.rollback_data['original_tmux_session'] = status.tmux_session
                
                status.migration_phase = MigrationPhase.PREPARATION
                logger.info(f"Prepared message queue for agent {agent_id}")
                
            except Exception as e:
                logger.error(f"Failed to prepare message queue for {agent_id}: {e}")
                status.error_count += 1
                
                if status.error_count >= self.config.max_error_count:
                    status.current_state = AgentMigrationState.MIGRATION_FAILED
    
    async def _activate_dual_mode(self):
        """Activate dual-mode operation for all agents."""
        logger.info("Activating dual-mode operation...")
        
        for agent_id, status in self.agent_statuses.items():
            if status.current_state == AgentMigrationState.MIGRATION_FAILED:
                continue
            
            try:
                # Start message queue monitoring for agent
                await self._start_message_queue_monitoring(agent_id)
                
                # Keep tmux communication active
                await self._verify_tmux_communication(agent_id)
                
                # Set dual mode state
                status.current_state = AgentMigrationState.DUAL_MODE
                status.migration_phase = MigrationPhase.DUAL_MODE_ACTIVATION
                
                logger.info(f"Agent {agent_id} is now in dual mode")
                
            except Exception as e:
                logger.error(f"Failed to activate dual mode for {agent_id}: {e}")
                status.error_count += 1
    
    async def _validate_dual_mode_operation(self):
        """Validate that dual-mode operation is working correctly."""
        logger.info("Validating dual-mode operation...")
        
        validation_start = datetime.now()
        validation_end = validation_start + timedelta(seconds=self.config.dual_mode_duration)
        
        while datetime.now() < validation_end:
            validation_round = datetime.now()
            
            for agent_id, status in self.agent_statuses.items():
                if status.current_state != AgentMigrationState.DUAL_MODE:
                    continue
                
                try:
                    # Test tmux communication
                    tmux_success = await self._test_tmux_communication(agent_id)
                    
                    # Test message queue communication  
                    queue_success = await self._test_message_queue_communication(agent_id)
                    
                    # Record validation results
                    status.validation_results[validation_round.isoformat()] = {
                        'tmux_success': tmux_success,
                        'queue_success': queue_success,
                        'both_working': tmux_success and queue_success
                    }
                    
                    if tmux_success:
                        status.last_tmux_activity = validation_round
                    if queue_success:
                        status.last_queue_activity = validation_round
                    
                except Exception as e:
                    logger.error(f"Validation failed for {agent_id}: {e}")
                    status.error_count += 1
            
            # Wait for next validation round
            await asyncio.sleep(self.config.validation_interval)
        
        # Analyze validation results
        await self._analyze_validation_results()
    
    async def _analyze_validation_results(self):
        """Analyze validation results and determine if cutover should proceed."""
        logger.info("Analyzing validation results...")
        
        for agent_id, status in self.agent_statuses.items():
            if status.current_state != AgentMigrationState.DUAL_MODE:
                continue
            
            validation_results = list(status.validation_results.values())
            if not validation_results:
                logger.warning(f"No validation results for {agent_id}")
                status.current_state = AgentMigrationState.MIGRATION_FAILED
                continue
            
            # Calculate success rates
            queue_successes = sum(1 for r in validation_results if r.get('queue_success', False))
            queue_success_rate = queue_successes / len(validation_results)
            
            both_successes = sum(1 for r in validation_results if r.get('both_working', False))
            both_success_rate = both_successes / len(validation_results)
            
            logger.info(f"Agent {agent_id} validation: queue={queue_success_rate:.2%}, both={both_success_rate:.2%}")
            
            # Check if agent is ready for cutover
            if queue_success_rate >= self.config.min_dual_mode_success_rate:
                status.migration_phase = MigrationPhase.VALIDATION
                logger.info(f"Agent {agent_id} ready for cutover")
            else:
                logger.warning(f"Agent {agent_id} validation failed, marking for rollback")
                status.current_state = AgentMigrationState.MIGRATION_FAILED
    
    async def _execute_cutover(self):
        """Execute cutover to message queue only."""
        logger.info("Executing cutover to message queue...")
        
        for agent_id, status in self.agent_statuses.items():
            if status.migration_phase != MigrationPhase.VALIDATION:
                continue
            
            try:
                # Stop tmux communication
                await self._stop_tmux_communication(agent_id)
                
                # Ensure message queue is primary
                await self._ensure_message_queue_primary(agent_id)
                
                # Update status
                status.current_state = AgentMigrationState.MESSAGE_QUEUE_ONLY
                status.migration_phase = MigrationPhase.CUTOVER
                
                logger.info(f"Agent {agent_id} cutover completed")
                
            except Exception as e:
                logger.error(f"Cutover failed for {agent_id}: {e}")
                status.error_count += 1
                status.current_state = AgentMigrationState.MIGRATION_FAILED
    
    async def _cleanup_tmux_infrastructure(self):
        """Clean up tmux infrastructure after successful migration."""
        logger.info("Cleaning up tmux infrastructure...")
        
        for agent_id, status in self.agent_statuses.items():
            if status.current_state != AgentMigrationState.MESSAGE_QUEUE_ONLY:
                continue
            
            try:
                # Remove tmux window
                await self._remove_tmux_window(agent_id)
                
                # Clean up rollback data
                status.rollback_data.clear()
                
                status.migration_phase = MigrationPhase.CLEANUP
                logger.info(f"Cleanup completed for agent {agent_id}")
                
            except Exception as e:
                logger.error(f"Cleanup failed for {agent_id}: {e}")
    
    async def _execute_rollback(self):
        """Execute rollback to tmux-only mode."""
        logger.info("Executing rollback to tmux-only mode...")
        
        for agent_id, status in self.agent_statuses.items():
            try:
                # Restore tmux communication
                await self._restore_tmux_communication(agent_id)
                
                # Disable message queue
                await self._disable_message_queue(agent_id)
                
                # Update status
                status.current_state = AgentMigrationState.TMUX_ONLY
                status.migration_phase = MigrationPhase.ROLLBACK
                
                logger.info(f"Agent {agent_id} rolled back to tmux-only")
                
            except Exception as e:
                logger.error(f"Rollback failed for {agent_id}: {e}")
    
    async def _check_tmux_activity(self, agent_id: str):
        """Check last tmux activity for an agent."""
        # Implementation would check tmux activity timestamps
        pass
    
    async def _start_message_queue_monitoring(self, agent_id: str):
        """Start message queue monitoring for an agent."""
        # Implementation would set up message queue monitoring
        pass
    
    async def _verify_tmux_communication(self, agent_id: str) -> bool:
        """Verify tmux communication is working."""
        # Implementation would test tmux communication
        return True
    
    async def _test_tmux_communication(self, agent_id: str) -> bool:
        """Test tmux communication."""
        try:
            status = self.agent_statuses[agent_id]
            
            # Send test message via tmux
            test_message = f"HEALTH_CHECK_{uuid.uuid4().hex[:8]}"
            cmd = ["tmux", "send-keys", "-t", f"{status.tmux_session}:{status.tmux_window}", test_message, "Enter"]
            
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, subprocess.run, cmd, 
                subprocess.PIPE, subprocess.PIPE, True
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Tmux communication test failed for {agent_id}: {e}")
            return False
    
    async def _test_message_queue_communication(self, agent_id: str) -> bool:
        """Test message queue communication."""
        try:
            # Send test message via message queue
            test_message = {
                "type": "health_check",
                "id": uuid.uuid4().hex[:8],
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id
            }
            
            # Implementation would send via event streaming
            success = await self.event_streaming.send_agent_message(agent_id, test_message)
            return success
            
        except Exception as e:
            logger.error(f"Message queue communication test failed for {agent_id}: {e}")
            return False
    
    async def _stop_tmux_communication(self, agent_id: str):
        """Stop tmux communication for an agent."""
        # Implementation would gracefully stop tmux communication
        pass
    
    async def _ensure_message_queue_primary(self, agent_id: str):
        """Ensure message queue is the primary communication method."""
        # Implementation would configure message queue as primary
        pass
    
    async def _remove_tmux_window(self, agent_id: str):
        """Remove tmux window for an agent."""
        try:
            status = self.agent_statuses[agent_id]
            cmd = ["tmux", "kill-window", "-t", f"{status.tmux_session}:{status.tmux_window}"]
            
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, subprocess.run, cmd, 
                subprocess.PIPE, subprocess.PIPE, True
            )
            
            if result.returncode != 0:
                logger.warning(f"Failed to remove tmux window for {agent_id}: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error removing tmux window for {agent_id}: {e}")
    
    async def _restore_tmux_communication(self, agent_id: str):
        """Restore tmux communication for an agent."""
        # Implementation would restore tmux communication
        pass
    
    async def _disable_message_queue(self, agent_id: str):
        """Disable message queue for an agent."""
        try:
            await self.event_streaming.unregister_agent_endpoint(agent_id)
        except Exception as e:
            logger.error(f"Failed to disable message queue for {agent_id}: {e}")
    
    def add_phase_callback(self, phase: MigrationPhase, callback: Callable):
        """Add a callback for a specific migration phase."""
        self.phase_callbacks[phase].append(callback)
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        return {
            "migration_id": self.migration_id,
            "migration_active": self.migration_active,
            "agents": {
                agent_id: {
                    "current_state": status.current_state.value,
                    "migration_phase": status.migration_phase.value,
                    "error_count": status.error_count,
                    "last_tmux_activity": status.last_tmux_activity.isoformat() if status.last_tmux_activity else None,
                    "last_queue_activity": status.last_queue_activity.isoformat() if status.last_queue_activity else None
                }
                for agent_id, status in self.agent_statuses.items()
            }
        }
    
    async def force_rollback(self, agent_id: Optional[str] = None):
        """Force rollback for specific agent or all agents."""
        if agent_id:
            agents_to_rollback = [agent_id] if agent_id in self.agent_statuses else []
        else:
            agents_to_rollback = list(self.agent_statuses.keys())
        
        for aid in agents_to_rollback:
            await self._restore_tmux_communication(aid)
            await self._disable_message_queue(aid)
            
            status = self.agent_statuses[aid]
            status.current_state = AgentMigrationState.TMUX_ONLY
            status.migration_phase = MigrationPhase.ROLLBACK
            
        logger.info(f"Force rollback completed for agents: {agents_to_rollback}")
    
    async def shutdown(self):
        """Shutdown migration manager."""
        if self.migration_active:
            logger.warning("Forcing rollback due to shutdown")
            await self.force_rollback()
        
        self.executor.shutdown(wait=True)
        logger.info("Migration Manager shutdown complete")