#!/usr/bin/env python3
"""
Fixed Agent Communication - Handles both prefixed and non-prefixed window names
Temporary fix until all agents use consistent naming
"""

import subprocess
import time
import sys
import argparse
from pathlib import Path

def send_message_to_agent_fixed(agent_name: str, message: str, auto_submit: bool = True) -> bool:
    """
    Send a message to an agent with automatic submission, handling both naming conventions.

    Args:
        agent_name: Target agent name (without agent- prefix)
        message: Message to send
        auto_submit: Whether to automatically submit with Enter

    Returns:
        bool: Success status
    """

    session_name = "agent-hive"