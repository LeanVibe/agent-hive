"""
Slack API Client for Integration Agent

Provides Slack integration including messaging, webhook handling,
and bot interactions for the agent-hive system.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass
import aiohttp
import hashlib
import hmac
from urllib.parse import urlencode


logger = logging.getLogger(__name__)


class SlackEventType(Enum):
    """Slack event types."""
    MESSAGE = "message"
    REACTION_ADDED = "reaction_added"
    REACTION_REMOVED = "reaction_removed"
    CHANNEL_CREATED = "channel_created"
    CHANNEL_DELETED = "channel_deleted"
    MEMBER_JOINED = "member_joined_channel"
    MEMBER_LEFT = "member_left_channel"
    APP_MENTION = "app_mention"
    FILE_SHARED = "file_shared"


class SlackMessageType(Enum):
    """Slack message types."""
    TEXT = "text"
    MARKDOWN = "mrkdwn"
    BLOCKS = "blocks"


@dataclass
class SlackConfig:
    """Slack API configuration."""
    bot_token: Optional[str] = None
    webhook_url: Optional[str] = None
    signing_secret: Optional[str] = None
    app_token: Optional[str] = None
    default_channel: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 1


@dataclass
class SlackMessage:
    """Slack message data."""
    channel: str
    text: str
    user: Optional[str] = None
    timestamp: Optional[str] = None
    thread_ts: Optional[str] = None
    message_type: SlackMessageType = SlackMessageType.TEXT
    attachments: Optional[List[Dict[str, Any]]] = None
    blocks: Optional[List[Dict[str, Any]]] = None


@dataclass
class SlackEvent:
    """Slack event data."""
    event_type: SlackEventType
    event_data: Dict[str, Any]
    team_id: str
    user_id: Optional[str] = None
    channel_id: Optional[str] = None
    timestamp: Optional[datetime] = None


class SlackAPIError(Exception):
    """Slack API error."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 response_data: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.response_data = response_data or {}
        super().__init__(message)


class SlackClient:
    """
    Slack API client for bot interactions and webhooks.
    
    Supports messaging, event handling, and integration with
    the agent-hive system.
    """
    
    def __init__(self, config: SlackConfig):
        """
        Initialize Slack client.
        
        Args:
            config: Slack API configuration
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://slack.com/api"
        
        # Event handlers
        self.event_handlers: Dict[SlackEventType, List[callable]] = {}
        
        # Request statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "messages_sent": 0,
            "events_processed": 0,
            "webhook_calls": 0
        }
        
        # Rate limiting
        self.rate_limit_info = {
            "calls_made": 0,
            "reset_time": 0,
            "tier": "default"
        }
        
        logger.info("SlackClient initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Connect to Slack API."""
        if self.session is None:
            headers = {
                "User-Agent": "LeanVibe-Agent-Hive/1.0",
                "Content-Type": "application/json"
            }
            
            if self.config.bot_token:
                headers["Authorization"] = f"Bearer {self.config.bot_token}"
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=100)
            )
            
            logger.info("Connected to Slack API")
    
    async def disconnect(self) -> None:
        """Disconnect from Slack API."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from Slack API")
    
    async def _make_request(self, endpoint: str, method: str = "POST", **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to Slack API.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        if not self.session:
            await self.connect()
        
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Check rate limits
                await self._check_rate_limit()
                
                # Make request
                async with self.session.request(method, url, **kwargs) as response:
                    # Update statistics
                    self.stats["total_requests"] += 1
                    
                    # Handle response
                    if response.status == 200:
                        response_data = await response.json()
                        
                        if response_data.get("ok"):
                            self.stats["successful_requests"] += 1
                            return response_data
                        else:
                            self.stats["failed_requests"] += 1
                            error_code = response_data.get("error", "unknown_error")
                            raise SlackAPIError(
                                f"Slack API error: {error_code}",
                                error_code,
                                response_data
                            )
                    elif response.status == 429:
                        # Rate limit hit
                        retry_after = int(response.headers.get("Retry-After", 1))
                        logger.warning(f"Rate limit hit. Retrying after {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        self.stats["failed_requests"] += 1
                        raise SlackAPIError(f"HTTP error: {response.status}")
                        
            except aiohttp.ClientError as e:
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                    continue
                else:
                    self.stats["failed_requests"] += 1
                    raise SlackAPIError(f"Connection error: {e}")
        
        self.stats["failed_requests"] += 1
        raise SlackAPIError(f"Max retries exceeded for {endpoint}")
    
    async def _check_rate_limit(self) -> None:
        """Check and handle rate limits."""
        current_time = time.time()
        
        # Basic rate limiting (Slack allows ~1 request per second for most endpoints)
        if self.rate_limit_info["calls_made"] > 0:
            time_since_last = current_time - self.rate_limit_info["reset_time"]
            if time_since_last < 1:
                await asyncio.sleep(1 - time_since_last)
        
        self.rate_limit_info["calls_made"] += 1
        self.rate_limit_info["reset_time"] = current_time
    
    # Messaging methods
    
    async def send_message(self, channel: str, text: str, 
                          thread_ts: Optional[str] = None,
                          attachments: Optional[List[Dict[str, Any]]] = None,
                          blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Send message to Slack channel.
        
        Args:
            channel: Channel ID or name
            text: Message text
            thread_ts: Thread timestamp for replies
            attachments: Message attachments
            blocks: Message blocks
            
        Returns:
            Message response data
        """
        data = {
            "channel": channel,
            "text": text
        }
        
        if thread_ts:
            data["thread_ts"] = thread_ts
        if attachments:
            data["attachments"] = attachments
        if blocks:
            data["blocks"] = blocks
        
        response = await self._make_request("chat.postMessage", json=data)
        self.stats["messages_sent"] += 1
        
        return response
    
    async def send_webhook_message(self, text: str, 
                                  attachments: Optional[List[Dict[str, Any]]] = None,
                                  blocks: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Send message via webhook.
        
        Args:
            text: Message text
            attachments: Message attachments
            blocks: Message blocks
            
        Returns:
            True if successful
        """
        if not self.config.webhook_url:
            raise SlackAPIError("Webhook URL not configured")
        
        data = {"text": text}
        
        if attachments:
            data["attachments"] = attachments
        if blocks:
            data["blocks"] = blocks
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.config.webhook_url, json=data) as response:
                self.stats["webhook_calls"] += 1
                
                if response.status == 200:
                    return True
                else:
                    raise SlackAPIError(f"Webhook error: {response.status}")
    
    async def send_formatted_message(self, channel: str, title: str, 
                                   message: str, color: str = "good",
                                   fields: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Send formatted message with attachment.
        
        Args:
            channel: Channel ID or name
            title: Message title
            message: Message text
            color: Attachment color
            fields: Additional fields
            
        Returns:
            Message response data
        """
        attachment = {
            "color": color,
            "title": title,
            "text": message,
            "footer": "LeanVibe Agent Hive",
            "ts": int(time.time())
        }
        
        if fields:
            attachment["fields"] = fields
        
        return await self.send_message(channel, "", attachments=[attachment])
    
    async def send_notification(self, message: str, 
                              channel: Optional[str] = None,
                              level: str = "info") -> Dict[str, Any]:
        """
        Send notification message.
        
        Args:
            message: Notification message
            channel: Target channel (uses default if not specified)
            level: Notification level (info, warning, error, success)
            
        Returns:
            Message response data
        """
        target_channel = channel or self.config.default_channel
        
        if not target_channel:
            raise SlackAPIError("No channel specified and no default channel configured")
        
        # Color mapping for different levels
        colors = {
            "info": "good",
            "success": "good",
            "warning": "warning",
            "error": "danger"
        }
        
        # Icon mapping for different levels
        icons = {
            "info": ":information_source:",
            "success": ":white_check_mark:",
            "warning": ":warning:",
            "error": ":x:"
        }
        
        color = colors.get(level, "good")
        icon = icons.get(level, ":speech_balloon:")
        
        formatted_message = f"{icon} {message}"
        
        return await self.send_formatted_message(
            target_channel,
            f"Agent Hive {level.title()}",
            formatted_message,
            color
        )
    
    # Channel methods
    
    async def list_channels(self, types: str = "public_channel,private_channel") -> List[Dict[str, Any]]:
        """
        List Slack channels.
        
        Args:
            types: Channel types to include
            
        Returns:
            List of channels
        """
        params = {"types": types}
        response = await self._make_request("conversations.list", method="GET", params=params)
        return response.get("channels", [])
    
    async def get_channel_info(self, channel: str) -> Dict[str, Any]:
        """
        Get channel information.
        
        Args:
            channel: Channel ID
            
        Returns:
            Channel information
        """
        params = {"channel": channel}
        response = await self._make_request("conversations.info", method="GET", params=params)
        return response.get("channel", {})
    
    async def join_channel(self, channel: str) -> Dict[str, Any]:
        """
        Join a channel.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            Join response data
        """
        data = {"channel": channel}
        return await self._make_request("conversations.join", json=data)
    
    # User methods
    
    async def get_user_info(self, user: str) -> Dict[str, Any]:
        """
        Get user information.
        
        Args:
            user: User ID
            
        Returns:
            User information
        """
        params = {"user": user}
        response = await self._make_request("users.info", method="GET", params=params)
        return response.get("user", {})
    
    async def list_users(self) -> List[Dict[str, Any]]:
        """
        List workspace users.
        
        Returns:
            List of users
        """
        response = await self._make_request("users.list", method="GET")
        return response.get("members", [])
    
    # Event handling
    
    def verify_webhook_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """
        Verify Slack webhook signature.
        
        Args:
            body: Request body
            timestamp: Request timestamp
            signature: Request signature
            
        Returns:
            True if signature is valid
        """
        if not self.config.signing_secret:
            return False
        
        # Create signature string
        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        
        # Generate expected signature
        expected_signature = "v0=" + hmac.new(
            self.config.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    async def process_event(self, event_data: Dict[str, Any]) -> SlackEvent:
        """
        Process incoming Slack event.
        
        Args:
            event_data: Event data from Slack
            
        Returns:
            Processed Slack event
        """
        event_type_str = event_data.get("type")
        
        if not event_type_str:
            raise SlackAPIError("Missing event type")
        
        try:
            event_type = SlackEventType(event_type_str)
        except ValueError:
            logger.warning(f"Unknown event type: {event_type_str}")
            # Create a generic event for unknown types
            event_type = SlackEventType.MESSAGE
        
        slack_event = SlackEvent(
            event_type=event_type,
            event_data=event_data,
            team_id=event_data.get("team_id", ""),
            user_id=event_data.get("user"),
            channel_id=event_data.get("channel"),
            timestamp=datetime.now()
        )
        
        # Trigger event handlers
        await self._trigger_event_handlers(slack_event)
        
        self.stats["events_processed"] += 1
        
        return slack_event
    
    def register_event_handler(self, event_type: SlackEventType, handler: callable) -> None:
        """
        Register event handler.
        
        Args:
            event_type: Event type to handle
            handler: Handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered event handler for {event_type.value}")
    
    async def _trigger_event_handlers(self, event: SlackEvent) -> None:
        """Trigger registered event handlers."""
        handlers = self.event_handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in Slack event handler: {e}")
    
    # Utility methods
    
    async def create_agent_notification_blocks(self, title: str, message: str, 
                                             agent_id: str, status: str) -> List[Dict[str, Any]]:
        """
        Create formatted blocks for agent notifications.
        
        Args:
            title: Notification title
            message: Notification message
            agent_id: Agent ID
            status: Agent status
            
        Returns:
            Slack blocks
        """
        # Status emoji mapping
        status_emojis = {
            "healthy": ":green_circle:",
            "unhealthy": ":red_circle:",
            "warning": ":yellow_circle:",
            "starting": ":blue_circle:",
            "stopping": ":white_circle:"
        }
        
        emoji = status_emojis.get(status.lower(), ":question:")
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *Agent:* {agent_id}\n*Status:* {status}\n*Message:* {message}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"LeanVibe Agent Hive • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            }
        ]
        
        return blocks
    
    async def send_agent_status_notification(self, agent_id: str, status: str, 
                                           message: str, channel: Optional[str] = None) -> Dict[str, Any]:
        """
        Send agent status notification.
        
        Args:
            agent_id: Agent ID
            status: Agent status
            message: Status message
            channel: Target channel
            
        Returns:
            Message response data
        """
        target_channel = channel or self.config.default_channel
        
        if not target_channel:
            raise SlackAPIError("No channel specified and no default channel configured")
        
        blocks = await self.create_agent_notification_blocks(
            "Agent Status Update",
            message,
            agent_id,
            status
        )
        
        return await self.send_message(target_channel, "", blocks=blocks)
    
    async def send_integration_summary(self, integrations: Dict[str, Any], 
                                     channel: Optional[str] = None) -> Dict[str, Any]:
        """
        Send integration status summary.
        
        Args:
            integrations: Integration status data
            channel: Target channel
            
        Returns:
            Message response data
        """
        target_channel = channel or self.config.default_channel
        
        if not target_channel:
            raise SlackAPIError("No channel specified and no default channel configured")
        
        # Build summary message
        summary_lines = []
        for name, info in integrations.items():
            status = info.get("status", "unknown")
            emoji = ":green_circle:" if status == "connected" else ":red_circle:"
            summary_lines.append(f"{emoji} *{name.title()}*: {status}")
        
        summary_text = "\n".join(summary_lines)
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Integration Status Summary"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary_text
                }
            }
        ]
        
        return await self.send_message(target_channel, "", blocks=blocks)
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test Slack connection.
        
        Returns:
            Connection test result
        """
        try:
            response = await self._make_request("auth.test", method="GET")
            return {
                "status": "connected",
                "team": response.get("team"),
                "user": response.get("user"),
                "bot_id": response.get("bot_id")
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "error": str(e)
            }
    
    def get_client_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.
        
        Returns:
            Client statistics
        """
        return {
            "stats": self.stats.copy(),
            "rate_limit": self.rate_limit_info.copy(),
            "event_handlers": {
                event_type.value: len(handlers)
                for event_type, handlers in self.event_handlers.items()
            },
            "connected": self.session is not None,
            "webhook_configured": self.config.webhook_url is not None,
            "bot_token_configured": self.config.bot_token is not None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Health check result
        """
        try:
            connection_test = await self.test_connection()
            
            if connection_test["status"] == "connected":
                return {
                    "status": "healthy",
                    "connected": True,
                    "connection_info": connection_test,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "error": connection_test.get("error"),
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }