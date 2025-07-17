#!/usr/bin/env python3
"""
LeanVibe Agent Hive CLI
Main command-line interface for the LeanVibe Agent Hive orchestration system.
"""

import argparse
import sys
from pathlib import Path

VERSION = "1.0.0"


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LeanVibe Agent Hive - Multi-agent orchestration system",
        prog="cli.py"
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"LeanVibe Agent Hive {VERSION}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Orchestrate command
    orchestrate_parser = subparsers.add_parser("orchestrate", help="Orchestrate multi-agent workflows")
    orchestrate_parser.add_argument("--config", help="Configuration file path")
    
    # Spawn command
    spawn_parser = subparsers.add_parser("spawn", help="Spawn new agents")
    spawn_parser.add_argument("agent_type", help="Type of agent to spawn")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor system status")
    monitor_parser.add_argument("--detailed", action="store_true", help="Show detailed monitoring")
    
    # Checkpoint command
    checkpoint_parser = subparsers.add_parser("checkpoint", help="Create system checkpoints")
    checkpoint_parser.add_argument("--name", help="Checkpoint name")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Route to appropriate handlers
    if args.command == "orchestrate":
        print(f"🎯 Orchestrating workflow with config: {args.config or 'default'}")
    elif args.command == "spawn":
        print(f"🚀 Spawning {args.agent_type} agent")
    elif args.command == "monitor":
        detail_level = "detailed" if args.detailed else "basic"
        print(f"📊 Monitoring system ({detail_level} mode)")
    elif args.command == "checkpoint":
        checkpoint_name = args.name or "auto"
        print(f"💾 Creating checkpoint: {checkpoint_name}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())