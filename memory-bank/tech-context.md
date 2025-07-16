# Tech Context: LeanVibe Agent Hive

## 1. Core Technologies

*   **Primary Language**: Python 3.12+
*   **Dependency Management**: [UV](https://docs.astral.sh/uv/) (recommended), with `requirements.txt` for traditional `pip` environments.
*   **JavaScript Tooling**: [Bun](https://bun.sh/) (optional, used for specific tutorial projects like the LitPWA frontend).
*   **AI Models**: Primarily designed for Claude instances, with capabilities to integrate other models like Gemini for specific tasks (e.g., reviews).

## 2. Development Environment Setup

### Prerequisites
*   **Operating System**: macOS 10.15+ (the system is optimized for and primarily tested on modern macOS).
*   **Version Control**: Git

### Recommended Installation
The recommended setup uses `uv` for a streamlined, all-in-one project and dependency management experience.

```bash
# 1. Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the repository
git clone https://github.com/leanvibe/agent-hive.git
cd agent-hive

# 3. Sync dependencies
uv sync

# 4. Run tests to verify setup
uv run pytest
```

## 3. Technical Constraints & Considerations

*   **macOS Optimization**: While the core logic is Python-based, many of the development and utility scripts may have macOS-specific commands. Functionality on Linux or Windows is not guaranteed without potential modifications.
*   **CLI-Driven System**: The primary interface for the agent hive is the `cli.py` script. All orchestration and management tasks are designed to be run from the command line.
*   **No Configuration Files (Yet)**: As noted in the `README.md`, the system is not yet configured via `.yaml` files in a `.claude/config` directory. Configuration is currently handled via environment variables or is pending future implementation.
