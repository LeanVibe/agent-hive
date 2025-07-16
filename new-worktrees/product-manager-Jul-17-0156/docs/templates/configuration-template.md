# [Component] Configuration Reference

**Status**: Current configuration options  
**Version**: X.Y.Z  
**Config File**: Path to configuration file  

## Overview
Description of configuration system and file locations.

## Configuration File Structure
```yaml
# Main configuration sections
section1:
  option1: value1
  option2: value2
  
section2:
  option3: value3
```

## Configuration Sections

### Section 1: [Name]
**Purpose**: What this section configures.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| option1 | string | "default" | Description of option1 |
| option2 | integer | 100 | Description of option2 |

**Example**:
```yaml
section1:
  option1: "custom_value"
  option2: 200
```

### Section 2: [Name]
Continue for each configuration section.

## Environment Variables
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| VAR_NAME | string | "default" | Environment variable description |

## Validation
How to validate configuration:
```bash
# Validation command
config validate
```

## Examples
Common configuration patterns and use cases.