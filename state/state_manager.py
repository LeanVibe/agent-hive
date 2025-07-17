#!/usr/bin/env python3
"""
StateManager - Centralized state management system for LeanVibe Agent Hive.

Provides comprehensive state management with SQLite backend, including agent states,
task states, checkpoints, and ML integration.

Usage:
  python state/state_manager.py --help
  python state/state_manager.py --rollback CHECKPOINT_ID
  python state/state_manager.py --list-checkpoints
"""

import argparse
import asyncio
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# ... (rest of the file unchanged)


def main():
    parser = argparse.ArgumentParser(
        description="StateManager - Centralized state management for LeanVibe Agent Hive."
    )
    parser.add_argument(
        "--rollback", type=int, help="Rollback to a specific checkpoint ID"
    )
    parser.add_argument(
        "--list-checkpoints", action="store_true", help="List all checkpoints"
    )
    args = parser.parse_args()

    sm = StateManager()
    if args.rollback:
        sm.rollback(args.rollback)
        print(f"Rolled back to checkpoint {args.rollback}.")
    elif args.list_checkpoints:
        checkpoints = sm.list_checkpoints()
        for cp in checkpoints:
            print(cp)
    else:
        print("StateManager ready. Use --help for options.")


if __name__ == "__main__":
    main()
