# /context - Enhanced Context Usage Monitor

Real-time context usage monitoring with configurable thresholds, automatic alerts, and trend analysis.

## Usage
```
/context [action] [parameters]
```

## Available Actions

### Status and Monitoring
- `/context` or `/context status` - Show detailed context status dashboard
- `/context check` - Quick context check with progress bar  
- `/context monitor [minutes]` - Monitor with alerts for specified duration (default: 60 minutes)
- `/context history [hours]` - Show usage history for N hours (default: 6 hours)

### Configuration
- `/context config` - Show current configuration
- `/context config reset` - Reset configuration to defaults
- `/context threshold <name> <value>` - Update specific threshold

### Help
- `/context help` - Show detailed help and examples

## Features

### 🎯 **Configurable Thresholds**
- **Light Consolidation** (default: 75%) - Triggers light memory consolidation
- **Critical Consolidation** (default: 85%) - Triggers critical memory consolidation  
- **Emergency Sleep** (default: 95%) - Triggers emergency sleep/wake cycle

### 📊 **Visual Progress Display**
- Color-coded progress bars (🟢🟡🟠🔴)
- Real-time percentage display
- Threshold status indicators
- Usage trend analysis (increasing/decreasing/stable)

### ⏰ **Predictive Analytics**
- Time estimates to critical/emergency thresholds
- Usage trend detection over time
- 24-hour usage history tracking
- Automatic alert system

### 🔔 **Smart Notifications**
- Threshold breach alerts (once per threshold)
- Automatic clearing when usage drops
- Configurable alert messages
- Integration with existing sleep/wake system

## Examples

### Quick Status Check
```bash
/context check
# Output: 🟡 Context: [🟡🟡🟡🟡🟡🟡🟡🟡⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜] 72.3% (warning)
```

### Detailed Status Dashboard  
```bash
/context status
# Shows:
# - Current usage percentage
# - Threshold status
# - Usage trend analysis  
# - Time estimates to thresholds
# - Configured threshold values
# - Recommended actions if needed
```

### Configure Thresholds
```bash
/context threshold consolidation_light 70
/context threshold consolidation_critical 80
/context threshold sleep_emergency 90
```

### Monitor with Alerts
```bash
/context monitor 30
# Monitors for 30 minutes and displays alerts when thresholds are reached
```

### View Usage History
```bash
/context history 12
# Shows usage statistics for the last 12 hours:
# - Min/Max/Average usage
# - Current usage and trend
# - Number of data points collected
```

## Configuration File

Configuration is stored in `.claude/config/context_thresholds.json`:

```json
{
  "thresholds": {
    "consolidation_light": 75,
    "consolidation_critical": 85, 
    "sleep_emergency": 95
  },
  "monitoring": {
    "check_interval_seconds": 300,
    "warning_advance_notice": 5,
    "enable_automatic_actions": true,
    "enable_background_monitoring": false
  },
  "actions": {
    "75_percent": {
      "action": "consolidate_light",
      "notify": true,
      "message": "🟡 Context usage at 75% - Light consolidation recommended"
    },
    "85_percent": {
      "action": "consolidate_critical",
      "notify": true, 
      "message": "🟠 Context usage at 85% - Critical consolidation required"
    },
    "95_percent": {
      "action": "sleep_emergency",
      "notify": true,
      "message": "🔴 Context usage at 95% - Emergency sleep/wake cycle required"  
    }
  },
  "display": {
    "show_percentage": true,
    "show_progress_bar": true,
    "progress_bar_width": 40,
    "color_coding": true
  }
}
```

## Integration with Existing Memory Management

### Automatic Actions
When automatic actions are enabled, the context monitor will:
- **75% threshold**: Trigger light memory consolidation
- **85% threshold**: Trigger critical memory consolidation  
- **95% threshold**: Trigger emergency sleep/wake cycle

### Integration Points
- Uses existing `ContextMemoryManager` for consolidation
- Works with existing `/sleep` and `/wake` commands
- Preserves all current memory management functionality
- Adds enhanced monitoring and prediction capabilities

## Threshold Recommendations

### Conservative (Recommended)
- Light: 70%, Critical: 80%, Emergency: 90%
- Provides early warning with ample response time

### Standard (Default)
- Light: 75%, Critical: 85%, Emergency: 95%
- Balanced approach for most use cases

### Aggressive  
- Light: 80%, Critical: 90%, Emergency: 95%
- Maximizes context usage but reduces response time

## Usage Patterns

### Development Sessions
```bash
/context check          # Quick status at session start
/context monitor 120    # Monitor for 2-hour development session
/context history 6      # Review usage after session
```

### Troubleshooting
```bash
/context status         # Detailed analysis of current state
/context config         # Review current configuration
/context threshold consolidation_critical 80  # Adjust if needed
```

### Preventive Monitoring
```bash
/context monitor 480    # 8-hour monitoring for long sessions
```

## Performance Impact

- **Minimal overhead**: Uses existing context calculation methods
- **Efficient storage**: Only keeps 24 hours of usage history
- **Smart caching**: Avoids redundant calculations
- **Configurable intervals**: Balance between responsiveness and efficiency

## Error Handling

- **Graceful degradation**: Falls back to defaults if config is corrupted
- **Safe threshold updates**: Validates values before applying
- **Backup configuration**: Automatic backup before changes
- **Recovery options**: Reset to defaults always available

---

**🎯 Purpose**: Provide proactive context usage awareness with predictive analytics to optimize Claude Code session management and prevent unexpected context limits.

**🔗 Related Commands**: `/sleep`, `/wake`, memory consolidation system

**📁 Files Created**:
- `.claude/config/context_thresholds.json` - Configuration
- `.claude/scripts/enhanced_context_monitor.py` - Core functionality