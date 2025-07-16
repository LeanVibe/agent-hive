#!/usr/bin/env python3
"""
Quick start script for the Message Queue Communication System.
Provides easy startup with sensible defaults.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add message_queue to path
sys.path.insert(0, str(Path(__file__).parent))

from message_queue.main import MessageQueueSystem


async def main():
    """Quick start with default configuration."""
    print("🚀 Starting Agent Hive Message Queue System")
    print("=" * 50)
    
    # Default configuration
    system = MessageQueueSystem(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        api_host=os.getenv("API_HOST", "localhost"), 
        api_port=int(os.getenv("API_PORT", "8080")),
        enable_monitoring=True,
        enable_migration=True
    )
    
    try:
        await system.run()
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ System error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())