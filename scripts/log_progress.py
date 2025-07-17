#!/usr/bin/env python3
"""
Agent Progress Logger - Quick Win #2 from Gemini Analysis
Standardized progress logging for all agents
"""

import argparse
from datetime import datetime
import os

def log_progress(agent_id: str, status: str, task: str, result: str = ""):
    """
    Log agent progress in standardized format
    
    Args:
        agent_id: Agent identifier
        status: START, PROGRESS, COMPLETE, STUCK, ERROR
        task: Brief task description
        result: Result or current state
    """
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {agent_id} | {status} | {task} | {result}\n"
    
    log_file = "/Users/bogdan/work/leanvibe-dev/agent-hive/progress_monitor.log"
    
    with open(log_file, "a") as f:
        f.write(log_line)
    
    print(f"✅ Logged: {agent_id} - {status} - {task}")

def main():
    parser = argparse.ArgumentParser(description="Log agent progress")
    parser.add_argument("--agent", required=True, help="Agent ID")
    parser.add_argument("--status", required=True, 
                       choices=["START", "PROGRESS", "COMPLETE", "STUCK", "ERROR"],
                       help="Current status")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--result", default="", help="Result or current state")
    
    args = parser.parse_args()
    
    log_progress(args.agent, args.status, args.task, args.result)

if __name__ == "__main__":
    main()