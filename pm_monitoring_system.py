#!/usr/bin/env python3
'''
PM Agent Health Monitoring System
Automated health checks and auto-respawn capabilities
'''

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

class PMMonitoringSystem:
    def __init__(self):
        self.health_log = Path("pm_health_monitor.log")
        self.status_file = Path("pm_agent_status.json")
        
    def health_check(self):
        '''Perform comprehensive health check'''
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "checks": {}
        }
        
        # Check git repository health
        try:
            result = subprocess.run(["git", "status"], capture_output=True, check=True)
            health_status["checks"]["git_status"] = "healthy"
        except subprocess.CalledProcessError:
            health_status["checks"]["git_status"] = "unhealthy"
            health_status["status"] = "degraded"
        
        # Check quality gate system
        try:
            if Path("quality_gate_enforcement.py").exists():
                health_status["checks"]["quality_gates"] = "operational"
            else:
                health_status["checks"]["quality_gates"] = "missing"
                health_status["status"] = "degraded"
        except Exception:
            health_status["checks"]["quality_gates"] = "error"
            health_status["status"] = "unhealthy"
        
        # Check prevention systems
        try:
            if Path("hooks/pre-commit-pr-size-check.py").exists():
                health_status["checks"]["prevention_hooks"] = "operational"
            else:
                health_status["checks"]["prevention_hooks"] = "missing"
                health_status["status"] = "degraded"
        except Exception:
            health_status["checks"]["prevention_hooks"] = "error"
            health_status["status"] = "unhealthy"
        
        # Log health status
        with open(self.health_log, "a") as f:
            f.write(json.dumps(health_status) + "\n")
        
        # Update status file
        with open(self.status_file, "w") as f:
            json.dump(health_status, f, indent=2)
        
        return health_status
    
    def monitor_loop(self, interval=300):  # 5 minutes
        '''Continuous monitoring loop'''
        while True:
            status = self.health_check()
            if status["status"] == "unhealthy":
                self.trigger_alert(status)
            time.sleep(interval)
    
    def trigger_alert(self, status):
        '''Trigger alert for unhealthy status'''
        alert = {
            "timestamp": datetime.now().isoformat(),
            "type": "health_alert",
            "status": status,
            "action": "pm_agent_attention_required"
        }
        
        # Log alert
        with open("pm_alerts.log", "a") as f:
            f.write(json.dumps(alert) + "\n")
        
        print(f"🚨 PM AGENT HEALTH ALERT: {status['status']}")
        print(f"Failed checks: {[k for k, v in status['checks'].items() if v != 'healthy' and v != 'operational']}")

if __name__ == "__main__":
    monitor = PMMonitoringSystem()
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        status = monitor.health_check()
        print(json.dumps(status, indent=2))
    else:
        monitor.monitor_loop()
