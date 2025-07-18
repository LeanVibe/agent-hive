#!/usr/bin/env python3
"""
LeanVibe PM Monitoring System
Prevention-First Approach: Health checks and auto-respawn system
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict


class PMMonitor:
    """Process Monitor for LeanVibe Agent Hive - Prevention-First Approach"""

    def __init__(self, config_path: str = "pm_monitor_config.json"):
        """Initialize PM Monitor with configuration."""
        self.config_path = config_path
        self.config = self._load_config()
        self.processes: Dict[str, dict] = {}
        self.health_checks: Dict[str, bool] = {}
        self.last_check_time = datetime.now()

        # Setup logging
        self._setup_logging()

    def _load_config(self) -> dict:
        """Load monitoring configuration."""
        default_config = {
            "check_interval": 30,  # seconds
            "max_restart_attempts": 3,
            "restart_cooldown": 60,  # seconds
            "health_check_timeout": 10,  # seconds
            "processes": {
                "cli": {
                    "command": ["python", "cli.py", "--help"],
                    "health_check": "cli_health_check",
                    "critical": True,
                    "auto_restart": True
                },
                "quality_gates": {
                    "command": ["python", "scripts/enhanced_quality_gates.py", "--status"],
                    "health_check": "quality_gates_health_check",
                    "critical": True,
                    "auto_restart": True
                }
            },
            "alerts": {
                "email": False,
                "webhook": False,
                "console": True
            }
        }

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            self._save_config(default_config)
            return default_config

    def _save_config(self, config: dict) -> None:
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "pm_monitor.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('PMMonitor')

    async def start_monitoring(self) -> None:
        """Start the monitoring loop."""
        self.logger.info("🚀 Starting LeanVibe PM Monitor")
        self.logger.info(
            "📋 Prevention-First Approach: Health checks and auto-respawn")

        try:
            while True:
                await self._monitor_cycle()
                await asyncio.sleep(self.config["check_interval"])
        except KeyboardInterrupt:
            self.logger.info("⏹️  PM Monitor stopped by user")
        except Exception as e:
            self.logger.error(f"❌ PM Monitor error: {e}")

    async def _monitor_cycle(self) -> None:
        """Execute one monitoring cycle."""
        self.logger.info("🔍 Starting monitoring cycle")

        # Check process health
        for process_name, process_config in self.config["processes"].items():
            await self._check_process_health(process_name, process_config)

        # Generate health report
        self._generate_health_report()

        # Check for critical alerts
        await self._check_critical_alerts()

        self.last_check_time = datetime.now()

    async def _check_process_health(
            self,
            process_name: str,
            process_config: dict) -> None:
        """Check health of a specific process."""
        self.logger.info(f"🔍 Checking health of {process_name}")

        try:
            # Run health check command
            if process_config.get("health_check"):
                health_method = getattr(
                    self, process_config["health_check"], None)
                if health_method:
                    is_healthy = await health_method(process_name, process_config)
                else:
                    is_healthy = await self._default_health_check(process_name, process_config)
            else:
                is_healthy = await self._default_health_check(process_name, process_config)

            # Update health status
            self.health_checks[process_name] = is_healthy

            if is_healthy:
                self.logger.info(f"✅ {process_name} is healthy")
                # Reset restart attempts on success
                if process_name in self.processes:
                    self.processes[process_name]["restart_attempts"] = 0
            else:
                self.logger.warning(f"⚠️  {process_name} health check failed")
                await self._handle_unhealthy_process(process_name, process_config)

        except Exception as e:
            self.logger.error(f"❌ Error checking {process_name}: {e}")
            self.health_checks[process_name] = False

    async def _default_health_check(
            self,
            process_name: str,
            process_config: dict) -> bool:
        """Default health check implementation."""
        try:
            # Run the command with timeout
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *process_config["command"],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=self.config["health_check_timeout"]
            )

            stdout, stderr = await result.communicate()
            return result.returncode == 0

        except asyncio.TimeoutError:
            self.logger.warning(f"⏱️  Health check timeout for {process_name}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Health check error for {process_name}: {e}")
            return False

    async def cli_health_check(
            self,
            process_name: str,
            process_config: dict) -> bool:
        """Specialized health check for CLI."""
        try:
            # Test CLI help command
            result = await asyncio.create_subprocess_exec(
                "python", "cli.py", "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                # Check if expected content is in output
                output = stdout.decode()
                return "LeanVibe Agent Hive" in output
            else:
                self.logger.error(
                    f"CLI health check failed: {stderr.decode()}")
                return False

        except Exception as e:
            self.logger.error(f"CLI health check error: {e}")
            return False

    async def quality_gates_health_check(
            self,
            process_name: str,
            process_config: dict) -> bool:
        """Specialized health check for quality gates."""
        try:
            # Check if quality gates script exists and is executable
            script_path = Path("scripts/enhanced_quality_gates.py")
            if not script_path.exists():
                self.logger.warning("Quality gates script not found")
                return False

            # Try to run status check
            result = await asyncio.create_subprocess_exec(
                "python", str(script_path), "--status",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()
            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Quality gates health check error: {e}")
            return False

    async def _handle_unhealthy_process(
            self,
            process_name: str,
            process_config: dict) -> None:
        """Handle unhealthy process detection."""
        if not process_config.get("auto_restart", False):
            self.logger.info(
                f"⚠️  {process_name} is unhealthy but auto-restart is disabled")
            return

        # Initialize process tracking if not exists
        if process_name not in self.processes:
            self.processes[process_name] = {
                "restart_attempts": 0,
                "last_restart": None
            }

        process_info = self.processes[process_name]

        # Check restart limits
        if process_info["restart_attempts"] >= self.config["max_restart_attempts"]:
            self.logger.error(
                f"❌ {process_name} exceeded max restart attempts")
            await self._send_alert(f"Process {process_name} failed permanently")
            return

        # Check cooldown period
        if process_info["last_restart"]:
            time_since_restart = datetime.now() - process_info["last_restart"]
            if time_since_restart.total_seconds(
            ) < self.config["restart_cooldown"]:
                self.logger.info(f"⏳ {process_name} in restart cooldown")
                return

        # Attempt restart
        await self._restart_process(process_name, process_config)

    async def _restart_process(
            self,
            process_name: str,
            process_config: dict) -> None:
        """Restart a failed process."""
        self.logger.info(f"🔄 Attempting to restart {process_name}")

        process_info = self.processes[process_name]
        process_info["restart_attempts"] += 1
        process_info["last_restart"] = datetime.now()

        try:
            # For CLI and quality gates, we don't actually restart long-running processes
            # Instead, we verify they can be started successfully
            result = await asyncio.create_subprocess_exec(
                *process_config["command"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                self.logger.info(f"✅ Successfully restarted {process_name}")
                await self._send_alert(f"Process {process_name} restarted successfully")
            else:
                self.logger.error(
                    f"❌ Failed to restart {process_name}: {stderr.decode()}")

        except Exception as e:
            self.logger.error(f"❌ Error restarting {process_name}: {e}")

    def _generate_health_report(self) -> None:
        """Generate and display health report."""
        healthy_count = sum(
            1 for status in self.health_checks.values() if status)
        total_count = len(self.health_checks)

        self.logger.info(
            f"📊 Health Report: {healthy_count}/{total_count} processes healthy")

        for process_name, is_healthy in self.health_checks.items():
            status = "✅ Healthy" if is_healthy else "❌ Unhealthy"
            self.logger.info(f"   {process_name}: {status}")

    async def _check_critical_alerts(self) -> None:
        """Check for critical system alerts."""
        critical_processes = [
            name for name, config in self.config["processes"].items()
            if config.get("critical", False)
        ]

        unhealthy_critical = [
            name for name in critical_processes
            if not self.health_checks.get(name, False)
        ]

        if unhealthy_critical:
            alert_message = f"🚨 Critical processes unhealthy: {
                ', '.join(unhealthy_critical)}"
            self.logger.error(alert_message)
            await self._send_alert(alert_message)

    async def _send_alert(self, message: str) -> None:
        """Send alert through configured channels."""
        if self.config["alerts"]["console"]:
            self.logger.warning(f"🚨 ALERT: {message}")

        # Add webhook/email alerts here if configured
        if self.config["alerts"]["webhook"]:
            # TODO: Implement webhook alerts
            pass

        if self.config["alerts"]["email"]:
            # TODO: Implement email alerts
            pass

    async def get_status(self) -> Dict[str, any]:
        """Get current monitoring status."""
        return {
            "monitoring_active": True,
            "last_check": self.last_check_time.isoformat(),
            "health_checks": self.health_checks,
            "processes": self.processes,
            "config": self.config
        }


async def main():
    """Main entry point for PM Monitor."""
    import argparse

    parser = argparse.ArgumentParser(description="LeanVibe PM Monitor")
    parser.add_argument("--config", default="pm_monitor_config.json",
                        help="Configuration file path")
    parser.add_argument("--status", action="store_true",
                        help="Show current status and exit")
    parser.add_argument("--check-once", action="store_true",
                        help="Run one monitoring cycle and exit")

    args = parser.parse_args()

    monitor = PMMonitor(args.config)

    if args.status:
        status = await monitor.get_status()
        print(json.dumps(status, indent=2))
        return

    if args.check_once:
        await monitor._monitor_cycle()
        return

    await monitor.start_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
