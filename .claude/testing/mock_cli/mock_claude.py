#!/usr/bin/env python3
"""Mock Claude CLI for testing purposes."""

import argparse
import json
import random
import sys
import time
from datetime import datetime


def simulate_success_response(prompt: str) -> dict:
    """Simulate successful Claude response."""
    return {
        "status": "success",
        "response": f"Mock Claude response to: {prompt[:100]}...",
        "confidence": random.uniform(0.7, 0.95),
        "timestamp": datetime.now().isoformat(),
        "model": "claude-3-5-sonnet-20241022",
        "usage": {
            "input_tokens": len(prompt.split()),
            "output_tokens": random.randint(50, 200)
        }
    }


def simulate_error_response(error_type: str = "generic") -> dict:
    """Simulate error response."""
    error_messages = {
        "timeout": "Request timed out after 30 seconds",
        "rate_limit": "Rate limit exceeded. Please try again later.",
        "invalid_input": "Invalid input format",
        "context_overflow": "Context window exceeded",
        "generic": "An unexpected error occurred"
    }

    return {
        "status": "error",
        "error": error_messages.get(error_type, error_messages["generic"]),
        "error_code": error_type,
        "timestamp": datetime.now().isoformat()
    }


def main():
    parser = argparse.ArgumentParser(description="Mock Claude CLI")
    parser.add_argument(
    "-p",
    "--prompt",
    required=True,
     help="Prompt to process")
    parser.add_argument("--error-type", help="Simulate specific error type")
    parser.add_argument(
    "--delay",
    type=float,
    default=1.0,
     help="Response delay in seconds")
    parser.add_argument(
    "--fail-rate",
    type=float,
    default=0.0,
     help="Failure rate (0.0-1.0)")
    parser.add_argument("--format", help="Output format (ignored)")
    parser.add_argument("--version", action="store_true", help="Show version")

    args = parser.parse_args()

    # Handle version request
    if args.version:
        print(json.dumps({"version": "mock-claude-1.0.0"}))
        sys.exit(0)

    # Simulate delay
    time.sleep(args.delay)

    # Simulate random failures
    if random.random() < args.fail_rate:
        response = simulate_error_response("generic")
        print(json.dumps(response, indent=2))
        sys.exit(1)

    # Simulate specific error if requested
    if args.error_type:
        response = simulate_error_response(args.error_type)
        print(json.dumps(response, indent=2))
        sys.exit(1)

    # Simulate success
    response = simulate_success_response(args.prompt)
    print(json.dumps(response, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
