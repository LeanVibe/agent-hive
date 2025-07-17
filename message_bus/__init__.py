"""
Production Message Bus Infrastructure for LeanVibe Agent Hive

Replaces tmux-based communication with Redis/RabbitMQ message bus system.
Provides reliable, scalable, production-ready agent communication.
"""

# Import core protocol components (no Redis dependency)
from .message_protocol import Message, MessageType, MessagePriority

# Import Redis-dependent components conditionally
try:
    from .message_bus import MessageBus, MessageBusConfig
    from .agent_communicator import AgentCommunicator, AgentRegistry
    from .reliability import MessageAcknowledgment, RetryManager, DeadLetterQueue

    __all__ = [
        "MessageBus",
        "MessageBusConfig",
        "AgentCommunicator",
        "AgentRegistry",
        "Message",
        "MessageType",
        "MessagePriority",
        "MessageAcknowledgment",
        "RetryManager",
        "DeadLetterQueue"
    ]
except ImportError as e:
    import warnings
    warnings.warn(f"Redis components not available: {e}. Only message protocol available.")

    __all__ = [
        "Message",
        "MessageType",
        "MessagePriority"
    ]
