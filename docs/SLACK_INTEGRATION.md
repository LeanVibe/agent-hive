# Slack Integration for LeanVibe Agent Hive

Real-time Slack notifications for priority changes, task completions, and sprint updates.

## Overview

The Slack integration provides lightweight, real-time notifications to keep your team informed of important changes in the LeanVibe Agent Hive system. Focus on high-value updates without noise.

### Key Features

- **Priority Change Alerts**: Immediate notifications when P0/P1/P2 items change priority
- **Completion Notifications**: Celebrate P0/P1 task completions 
- **Sprint Milestones**: Track progress at 25%, 50%, 75%, and 100% completion
- **Custom Messages**: Send ad-hoc notifications for important updates
- **Smart Filtering**: Prevent notification spam with intelligent filtering
- **Easy Configuration**: Environment variable configuration for security

## Quick Setup

### 1. Get Slack Webhook URL

1. Go to your Slack workspace
2. Navigate to Apps → Incoming Webhooks
3. Create a new webhook for your desired channel
4. Copy the webhook URL (starts with `https://hooks.slack.com/services/...`)

### 2. Configure Environment

```bash
# Set webhook URL (required)
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Optional: customize channel and settings
export SLACK_CHANNEL="#agent-hive-notifications"
export SLACK_USERNAME="LeanVibe Agent Hive"
```

### 3. Test Connection

```bash
# Test Slack integration
python cli.py slack --action test

# Send test notification
python cli.py slack --action test-notification --notification-type priority
```

## Usage

### Command Line Interface

#### View Configuration
```bash
python cli.py slack --action status
```

#### Send Custom Notification
```bash
python cli.py slack --action send \
  --title "Deployment Ready" \
  --message "Version 1.2.0 ready for production deployment" \
  --priority high
```

#### Manual Priority Change Notification
```bash
python cli.py slack --action notify-priority \
  --item-id "TASK-123" \
  --title "Fix critical authentication bug" \
  --old-priority "P2" \
  --new-priority "P0"
```

#### Manual Completion Notification
```bash
python cli.py slack --action notify-completion \
  --item-id "TASK-456" \
  --title "Implement user authentication system" \
  --priority "P1"
```

#### Check for Events
```bash
# Scan for priority changes and completions
python cli.py slack --action check-events
```

### Programmatic Integration

```python
import asyncio
from integrations.slack.slack_notifier import SlackNotifier, SlackNotificationConfig
from integrations.slack.event_detector import EventDetector

async def setup_notifications():
    # Configure notifier
    config = SlackNotificationConfig(
        webhook_url="https://hooks.slack.com/services/...",
        channel="#agent-hive-notifications"
    )
    
    notifier = SlackNotifier(config)
    detector = EventDetector(notifier)
    
    # Check for events and send notifications
    events = await detector.check_for_changes()
    print(f"Processed {len(events)} events")

asyncio.run(setup_notifications())
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SLACK_WEBHOOK_URL` | Slack webhook URL (required) | None |
| `SLACK_CHANNEL` | Target channel | `#agent-hive-notifications` |
| `SLACK_USERNAME` | Bot username | `LeanVibe Agent Hive` |
| `SLACK_ICON_EMOJI` | Bot icon | `:robot_face:` |
| `SLACK_MAX_RETRIES` | Max retry attempts | `3` |
| `SLACK_TIMEOUT` | Request timeout (seconds) | `10` |

### Configuration File

Create `config/slack_config.json` for advanced settings:

```json
{
  "webhook_url": "",
  "channel": "#agent-hive-notifications",
  "username": "LeanVibe Agent Hive",
  "icon_emoji": ":robot_face:",
  
  "notifications": {
    "priority_changes": {
      "enabled": true,
      "min_priority": "P2"
    },
    "completions": {
      "enabled": true,
      "min_priority": "P1"
    },
    "sprint_updates": {
      "enabled": true,
      "milestone_threshold": 25.0
    }
  },
  
  "delivery_settings": {
    "max_retries": 3,
    "timeout_seconds": 10,
    "enable_threading": true,
    "rate_limit_per_minute": 30
  }
}
```

## Event Detection

### BACKLOG.md Integration

The system automatically detects changes in BACKLOG.md files:

```markdown
# Project Backlog

- [TODO] P1: Implement user authentication #123 @john
- [IN_PROGRESS] P0: Fix critical security vulnerability #124 @sarah  
- [DONE] P2: Update documentation #125 @mike
```

Supported formats:
- `[STATUS] PRIORITY: Title #ID @assignee`
- Status: `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`
- Priority: `P0`, `P1`, `P2`, `P3`

### Git Commit Detection

Detects completions from commit messages:

```bash
git commit -m "Complete user authentication implementation #123"
git commit -m "Finish P1 security audit #124"
git commit -m "Done: API documentation update"
```

### Manual Triggers

Use CLI commands or API calls to manually trigger notifications:

```python
# Manual priority change
await detector.manually_trigger_priority_change(
    item_id="TASK-123",
    item_title="Critical bug fix",
    old_priority="P2",
    new_priority="P0",
    changed_by="Project Manager"
)

# Manual completion
await detector.manually_trigger_completion(
    item_id="TASK-456", 
    item_title="Feature implementation",
    priority="P1",
    completed_by="Development Team"
)
```

## Message Templates

### Priority Change Notification

```
🚨 **Priority Change Alert**

Item: Critical Authentication Bug
Priority Change: P2 ⬆️ P0
Changed By: Project Manager
Action Required: 🔥 *Immediate attention needed*
```

### Completion Notification

```
✅ **Task Completed** - P1

Completed Item: User Authentication System
Priority: ⚡ P1 - High
Completed By: Development Team
Next Steps: Deploy to staging environment
```

### Sprint Update

```
📊 **Sprint Update** - 75% Complete

Progress: ████████████████████░░░░ 75.0%
Completed Items: 8
Recently Completed:
• User authentication system
• API documentation
• Security audit
• ... and 5 more
```

## Automation Integration

### Git Hooks

Add to `.git/hooks/post-commit`:

```bash
#!/bin/bash
# Auto-check for notifications after commits
python cli.py slack --action check-events
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Send Slack notification
  run: |
    python cli.py slack --action send \
      --title "Build Complete" \
      --message "Build ${{ github.run_number }} completed successfully" \
      --priority medium
```

### Cron Job for Regular Checks

```bash
# Check for events every 15 minutes
*/15 * * * * cd /path/to/agent-hive && python cli.py slack --action check-events
```

## Security Considerations

- **Never commit webhook URLs** to version control
- **Use environment variables** for sensitive configuration
- **Limit webhook permissions** to specific channels
- **Configure rate limiting** to prevent spam
- **Monitor webhook usage** in Slack admin panel

## Troubleshooting

### Common Issues

#### Webhook URL Not Configured
```
❌ Slack not configured. Set SLACK_WEBHOOK_URL environment variable.
```
**Solution**: Set the `SLACK_WEBHOOK_URL` environment variable

#### Connection Failed
```
❌ Slack connection failed.
```
**Solutions**:
- Verify webhook URL is correct
- Check network connectivity
- Ensure Slack workspace allows incoming webhooks
- Verify webhook hasn't been revoked

#### No Events Detected
```
ℹ️ No events detected.
```
**Solutions**:
- Check BACKLOG.md file exists and has correct format
- Verify recent git commits have completion keywords
- Use manual triggers to test notification delivery

### Testing Commands

```bash
# Test configuration
python cli.py slack --action status

# Test connection
python cli.py slack --action test

# Test each notification type
python cli.py slack --action test-notification --notification-type priority
python cli.py slack --action test-notification --notification-type completion
python cli.py slack --action test-notification --notification-type sprint

# Run integration tests
python integrations/slack/test_integration.py
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Examples

### Complete Setup Script

```bash
#!/bin/bash
# setup-slack-notifications.sh

# Configure Slack webhook
read -p "Enter Slack webhook URL: " WEBHOOK_URL
export SLACK_WEBHOOK_URL="$WEBHOOK_URL"

# Test connection
echo "Testing Slack connection..."
python cli.py slack --action test

# Send welcome notification
python cli.py slack --action send \
  --title "Slack Integration Active" \
  --message "LeanVibe Agent Hive notifications are now active!" \
  --priority medium

# Setup cron job for automatic checks
echo "*/15 * * * * cd $(pwd) && python cli.py slack --action check-events" | crontab -

echo "✅ Slack integration setup complete!"
```

### Integration with Existing Workflows

```python
# Example: Integration with issue tracker
async def on_issue_priority_changed(issue_id, old_priority, new_priority):
    from integrations.slack.event_detector import EventDetector
    from integrations.slack.slack_notifier import SlackNotifier, SlackNotificationConfig
    
    config = SlackNotificationConfig(webhook_url=os.getenv("SLACK_WEBHOOK_URL"))
    notifier = SlackNotifier(config)
    detector = EventDetector(notifier)
    
    await detector.manually_trigger_priority_change(
        item_id=issue_id,
        item_title=f"Issue {issue_id}",
        old_priority=old_priority,
        new_priority=new_priority,
        changed_by="Issue Tracker"
    )
```

## Support

For issues and questions:

1. Check configuration with `python cli.py slack --action status`
2. Test connection with `python cli.py slack --action test`
3. Review logs for error details
4. Consult Slack webhook documentation
5. File issue in project repository

---

*LeanVibe Agent Hive - Slack Integration v1.0*