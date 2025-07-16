# First Project Tutorial

Build your first autonomous agent workflow with LeanVibe Agent Hive in just 15 minutes.

## What You'll Build

By the end of this tutorial, you'll have:
- A working multi-agent system
- An automated code review workflow  
- A simple web scraper agent
- Experience with agent coordination

## Prerequisites

- LeanVibe Agent Hive installed ([Installation Guide](installation.md))
- Basic Python knowledge
- 15-20 minutes of time

## Project Overview

We'll create a **Code Review Assistant** that:
1. **Scraper Agent**: Fetches code from GitHub
2. **Analyzer Agent**: Reviews code quality
3. **Reporter Agent**: Generates summary reports
4. **Coordinator**: Manages the workflow

## Step 1: Project Setup

### Create Project Directory

```bash
# Create and enter project directory
mkdir my-first-agent-project
cd my-first-agent-project

# Initialize project
leanvibe init code-review-assistant
```

### Project Structure

```
my-first-agent-project/
├── agents/
│   ├── scraper.py
│   ├── analyzer.py
│   └── reporter.py
├── config/
│   └── workflow.yaml
├── .env
└── main.py
```

## Step 2: Create the Scraper Agent

Create `agents/scraper.py`:

```python
from leanvibe import Agent, Task
import requests
import base64

class GitHubScraperAgent(Agent):
    """Agent that fetches code from GitHub repositories."""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, agent_type="scraper")
        self.capabilities = ["fetch_code", "parse_repository"]
    
    async def process_task(self, task: Task) -> dict:
        """Fetch code from a GitHub repository."""
        repo_url = task.inputs.get("repo_url")
        file_path = task.inputs.get("file_path", "")
        
        try:
            # Extract repo info from URL
            repo_info = self._parse_github_url(repo_url)
            
            # Fetch file content
            content = await self._fetch_file_content(repo_info, file_path)
            
            return {
                "status": "success",
                "code_content": content,
                "file_path": file_path,
                "repo_info": repo_info,
                "lines_of_code": len(content.split('\n')) if content else 0
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "file_path": file_path
            }
    
    def _parse_github_url(self, url: str) -> dict:
        """Parse GitHub URL to extract owner and repo."""
        # Simple parsing for demo - improve for production
        parts = url.replace("https://github.com/", "").split("/")
        return {
            "owner": parts[0],
            "repo": parts[1],
            "url": url
        }
    
    async def _fetch_file_content(self, repo_info: dict, file_path: str) -> str:
        """Fetch file content from GitHub API."""
        api_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/contents/{file_path}"
        
        response = requests.get(api_url)
        response.raise_for_status()
        
        # Decode base64 content
        content_data = response.json()
        if content_data.get("encoding") == "base64":
            return base64.b64decode(content_data["content"]).decode('utf-8')
        
        return content_data.get("content", "")

# Register agent
def create_agent():
    return GitHubScraperAgent("github-scraper")
```

## Step 3: Create the Analyzer Agent

Create `agents/analyzer.py`:

```python
from leanvibe import Agent, Task
import re
import ast

class CodeAnalyzerAgent(Agent):
    """Agent that analyzes code quality and provides feedback."""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, agent_type="analyzer")
        self.capabilities = ["analyze_code", "quality_check", "generate_feedback"]
    
    async def process_task(self, task: Task) -> dict:
        """Analyze code content for quality issues."""
        code_content = task.inputs.get("code_content")
        file_path = task.inputs.get("file_path", "")
        
        if not code_content:
            return {"status": "error", "error": "No code content provided"}
        
        try:
            analysis = await self._analyze_code(code_content, file_path)
            
            return {
                "status": "success",
                "file_path": file_path,
                "analysis": analysis,
                "quality_score": analysis["quality_score"],
                "recommendations": analysis["recommendations"]
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e),
                "file_path": file_path
            }
    
    async def _analyze_code(self, code: str, file_path: str) -> dict:
        """Perform comprehensive code analysis."""
        analysis = {
            "file_path": file_path,
            "lines_of_code": len(code.split('\n')),
            "issues": [],
            "recommendations": [],
            "quality_score": 100
        }
        
        # Check for Python syntax (if .py file)
        if file_path.endswith('.py'):
            analysis.update(await self._analyze_python_code(code))
        else:
            analysis.update(await self._analyze_general_code(code))
        
        # Calculate quality score
        analysis["quality_score"] = max(0, 100 - len(analysis["issues"]) * 10)
        
        return analysis
    
    async def _analyze_python_code(self, code: str) -> dict:
        """Analyze Python-specific code quality."""
        issues = []
        recommendations = []
        
        try:
            # Parse AST to check syntax
            ast.parse(code)
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        
        # Check for common issues
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Long lines
            if len(line) > 100:
                issues.append(f"Line {i}: Line too long ({len(line)} chars)")
            
            # TODO comments
            if "TODO" in line.upper():
                issues.append(f"Line {i}: TODO comment found")
            
            # Print statements (could be debug code)
            if re.search(r'\bprint\s*\(', line):
                recommendations.append(f"Line {i}: Consider using logging instead of print")
        
        # Check for docstrings
        if 'def ' in code and '"""' not in code:
            recommendations.append("Consider adding docstrings to functions")
        
        return {"issues": issues, "recommendations": recommendations}
    
    async def _analyze_general_code(self, code: str) -> dict:
        """Analyze general code quality."""
        issues = []
        recommendations = []
        
        lines = code.split('\n')
        
        # Check for common issues
        for i, line in enumerate(lines, 1):
            # Very long lines
            if len(line) > 120:
                issues.append(f"Line {i}: Very long line ({len(line)} chars)")
            
            # Trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                issues.append(f"Line {i}: Trailing whitespace")
        
        # Check for comments
        comment_lines = sum(1 for line in lines if line.strip().startswith('#') or line.strip().startswith('//'))
        if comment_lines / len(lines) < 0.1:
            recommendations.append("Consider adding more comments to explain code logic")
        
        return {"issues": issues, "recommendations": recommendations}

# Register agent
def create_agent():
    return CodeAnalyzerAgent("code-analyzer")
```

## Step 4: Create the Reporter Agent

Create `agents/reporter.py`:

```python
from leanvibe import Agent, Task
from datetime import datetime
import json

class ReportGeneratorAgent(Agent):
    """Agent that generates comprehensive reports from analysis results."""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, agent_type="reporter")
        self.capabilities = ["generate_report", "format_results", "create_summary"]
    
    async def process_task(self, task: Task) -> dict:
        """Generate a comprehensive code review report."""
        analysis_results = task.inputs.get("analysis_results", [])
        repo_info = task.inputs.get("repo_info", {})
        
        if not analysis_results:
            return {"status": "error", "error": "No analysis results provided"}
        
        try:
            report = await self._generate_report(analysis_results, repo_info)
            
            return {
                "status": "success",
                "report": report,
                "summary": report["summary"],
                "report_file": await self._save_report(report)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _generate_report(self, results: list, repo_info: dict) -> dict:
        """Generate comprehensive analysis report."""
        timestamp = datetime.now().isoformat()
        
        # Calculate overall statistics
        total_files = len(results)
        total_issues = sum(len(r.get("analysis", {}).get("issues", [])) for r in results)
        total_recommendations = sum(len(r.get("analysis", {}).get("recommendations", [])) for r in results)
        average_quality = sum(r.get("analysis", {}).get("quality_score", 0) for r in results) / total_files if total_files > 0 else 0
        
        # Categorize issues
        critical_issues = []
        warnings = []
        suggestions = []
        
        for result in results:
            analysis = result.get("analysis", {})
            file_path = result.get("file_path", "unknown")
            
            for issue in analysis.get("issues", []):
                if "syntax error" in issue.lower():
                    critical_issues.append(f"{file_path}: {issue}")
                elif "todo" in issue.lower():
                    suggestions.append(f"{file_path}: {issue}")
                else:
                    warnings.append(f"{file_path}: {issue}")
        
        # Create summary
        summary = {
            "overall_quality": "excellent" if average_quality >= 90 else "good" if average_quality >= 70 else "needs_improvement",
            "quality_score": round(average_quality, 1),
            "total_files_analyzed": total_files,
            "critical_issues_count": len(critical_issues),
            "warnings_count": len(warnings),
            "suggestions_count": len(suggestions) + total_recommendations
        }
        
        # Build full report
        report = {
            "metadata": {
                "generated_at": timestamp,
                "repository": repo_info.get("url", "unknown"),
                "analyzer_version": "1.0.0"
            },
            "summary": summary,
            "detailed_results": {
                "files_analyzed": results,
                "critical_issues": critical_issues,
                "warnings": warnings,
                "suggestions": suggestions
            },
            "recommendations": await self._generate_recommendations(summary, results)
        }
        
        return report
    
    async def _generate_recommendations(self, summary: dict, results: list) -> list:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        if summary["critical_issues_count"] > 0:
            recommendations.append("🚨 Fix critical syntax errors before proceeding with development")
        
        if summary["quality_score"] < 70:
            recommendations.append("📈 Focus on improving overall code quality")
            recommendations.append("📝 Add more comments and documentation")
        
        if summary["warnings_count"] > 10:
            recommendations.append("⚠️  Address code style and formatting issues")
        
        # Analyze patterns in results
        long_line_files = [r for r in results if any("Line too long" in issue for issue in r.get("analysis", {}).get("issues", []))]
        if len(long_line_files) > len(results) / 2:
            recommendations.append("📏 Consider setting up automatic line length formatting")
        
        todo_files = [r for r in results if any("TODO" in issue for issue in r.get("analysis", {}).get("issues", []))]
        if len(todo_files) > 3:
            recommendations.append("✅ Create issues for TODO comments to track pending work")
        
        if summary["quality_score"] >= 90:
            recommendations.append("🎉 Excellent code quality! Consider this as a template for other projects")
        
        return recommendations
    
    async def _save_report(self, report: dict) -> str:
        """Save report to file and return filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"code_review_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Also create a markdown summary
        md_filename = f"code_review_summary_{timestamp}.md"
        await self._create_markdown_report(report, md_filename)
        
        return filename
    
    async def _create_markdown_report(self, report: dict, filename: str):
        """Create a human-readable markdown report."""
        summary = report["summary"]
        
        md_content = f"""# Code Review Report
        
## Summary
- **Overall Quality**: {summary["overall_quality"].title()}
- **Quality Score**: {summary["quality_score"]}/100
- **Files Analyzed**: {summary["total_files_analyzed"]}

## Issues Found
- 🚨 **Critical Issues**: {summary["critical_issues_count"]}
- ⚠️  **Warnings**: {summary["warnings_count"]}
- 💡 **Suggestions**: {summary["suggestions_count"]}

## Recommendations
"""
        
        for rec in report["recommendations"]:
            md_content += f"- {rec}\n"
        
        md_content += f"""
## Details
Generated on: {report["metadata"]["generated_at"]}
Repository: {report["metadata"]["repository"]}

---
*Report generated by LeanVibe Agent Hive Code Review Assistant*
"""
        
        with open(filename, 'w') as f:
            f.write(md_content)

# Register agent
def create_agent():
    return ReportGeneratorAgent("report-generator")
```

## Step 5: Create the Workflow Configuration

Create `config/workflow.yaml`:

```yaml
# Code Review Assistant Workflow Configuration
workflow:
  name: "code-review-assistant"
  description: "Automated code review using multiple specialized agents"
  version: "1.0.0"

agents:
  - id: "github-scraper"
    type: "scraper"
    module: "agents.scraper"
    max_concurrent_tasks: 3
    timeout: 30
    
  - id: "code-analyzer"
    type: "analyzer" 
    module: "agents.analyzer"
    max_concurrent_tasks: 5
    timeout: 60
    
  - id: "report-generator"
    type: "reporter"
    module: "agents.reporter"
    max_concurrent_tasks: 1
    timeout: 120

coordination:
  strategy: "pipeline"
  retry_policy:
    max_retries: 3
    backoff_factor: 2
  
  pipeline:
    - stage: "fetch"
      agents: ["github-scraper"]
      parallelism: 3
      
    - stage: "analyze"
      agents: ["code-analyzer"]
      depends_on: ["fetch"]
      parallelism: 5
      
    - stage: "report"
      agents: ["report-generator"]
      depends_on: ["analyze"]
      parallelism: 1

monitoring:
  enabled: true
  log_level: "INFO"
  metrics: ["task_duration", "success_rate", "agent_utilization"]
```

## Step 6: Create the Main Application

Create `main.py`:

```python
#!/usr/bin/env python3
"""
Code Review Assistant - First LeanVibe Agent Project
"""

import asyncio
import sys
from leanvibe import MultiAgentCoordinator, Task
from agents.scraper import create_agent as create_scraper
from agents.analyzer import create_agent as create_analyzer  
from agents.reporter import create_agent as create_reporter

class CodeReviewAssistant:
    """Main application orchestrating the code review workflow."""
    
    def __init__(self):
        self.coordinator = MultiAgentCoordinator()
        self.setup_agents()
    
    def setup_agents(self):
        """Initialize and register all agents."""
        # Create agent instances
        scraper = create_scraper()
        analyzer = create_analyzer()
        reporter = create_reporter()
        
        # Register with coordinator
        self.coordinator.register_agent(scraper)
        self.coordinator.register_agent(analyzer)
        self.coordinator.register_agent(reporter)
        
        print("✅ All agents registered successfully")
    
    async def review_repository(self, repo_url: str, files_to_review: list = None):
        """Run complete code review workflow on a repository."""
        print(f"🚀 Starting code review for: {repo_url}")
        
        # Default files to review if none specified
        if not files_to_review:
            files_to_review = ["README.md", "src/main.py", "setup.py"]
        
        try:
            # Stage 1: Fetch code files
            print("📥 Stage 1: Fetching code files...")
            fetch_tasks = []
            for file_path in files_to_review:
                task = Task(
                    task_id=f"fetch-{file_path.replace('/', '-')}",
                    task_type="fetch_code",
                    inputs={"repo_url": repo_url, "file_path": file_path},
                    priority=5
                )
                fetch_tasks.append(task)
            
            fetch_results = []
            for task in fetch_tasks:
                result = await self.coordinator.execute_task("github-scraper", task)
                if result.get("status") == "success":
                    fetch_results.append(result)
                    print(f"  ✅ Fetched: {task.inputs['file_path']}")
                else:
                    print(f"  ❌ Failed to fetch: {task.inputs['file_path']}")
            
            if not fetch_results:
                print("❌ No files could be fetched. Aborting.")
                return None
            
            # Stage 2: Analyze code quality
            print("🔍 Stage 2: Analyzing code quality...")
            analysis_results = []
            for fetch_result in fetch_results:
                task = Task(
                    task_id=f"analyze-{fetch_result['file_path'].replace('/', '-')}",
                    task_type="analyze_code", 
                    inputs={
                        "code_content": fetch_result["code_content"],
                        "file_path": fetch_result["file_path"]
                    },
                    priority=5
                )
                
                result = await self.coordinator.execute_task("code-analyzer", task)
                if result.get("status") == "success":
                    analysis_results.append(result)
                    score = result.get("quality_score", 0)
                    print(f"  ✅ Analyzed: {result['file_path']} (Quality: {score}/100)")
                else:
                    print(f"  ❌ Failed to analyze: {fetch_result['file_path']}")
            
            # Stage 3: Generate report
            print("📊 Stage 3: Generating report...")
            report_task = Task(
                task_id="generate-report",
                task_type="generate_report",
                inputs={
                    "analysis_results": analysis_results,
                    "repo_info": {"url": repo_url}
                },
                priority=10
            )
            
            report_result = await self.coordinator.execute_task("report-generator", report_task)
            
            if report_result.get("status") == "success":
                print("✅ Code review completed successfully!")
                return report_result
            else:
                print("❌ Failed to generate report")
                return None
                
        except Exception as e:
            print(f"❌ Error during code review: {e}")
            return None
    
    async def print_summary(self, report_result: dict):
        """Print a summary of the code review results."""
        if not report_result or report_result.get("status") != "success":
            return
        
        summary = report_result["summary"]
        
        print("\n" + "="*50)
        print("📋 CODE REVIEW SUMMARY")
        print("="*50)
        print(f"Overall Quality: {summary['overall_quality'].title()}")
        print(f"Quality Score: {summary['quality_score']}/100")
        print(f"Files Analyzed: {summary['total_files_analyzed']}")
        print(f"Critical Issues: {summary['critical_issues_count']}")
        print(f"Warnings: {summary['warnings_count']}")
        print(f"Suggestions: {summary['suggestions_count']}")
        
        print(f"\n📁 Report saved to: {report_result.get('report_file', 'report.json')}")
        
        recommendations = report_result["report"]["recommendations"]
        if recommendations:
            print("\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"  {rec}")
        
        print("\n🎉 Your first LeanVibe Agent project is complete!")

async def main():
    """Main application entry point."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <github-repo-url> [file1] [file2] ...")
        print("Example: python main.py https://github.com/octocat/Hello-World main.py README.md")
        return
    
    repo_url = sys.argv[1]
    files_to_review = sys.argv[2:] if len(sys.argv) > 2 else None
    
    # Create and run the assistant
    assistant = CodeReviewAssistant()
    
    # Run the code review
    result = await assistant.review_repository(repo_url, files_to_review)
    
    # Print summary
    await assistant.print_summary(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 7: Environment Configuration

Create `.env`:

```bash
# LeanVibe Configuration
LEANVIBE_ENV=development
LEANVIBE_LOG_LEVEL=INFO
LEANVIBE_MAX_AGENTS=10

# GitHub API (optional - for higher rate limits)
# GITHUB_TOKEN=your_github_token_here

# Agent Configuration
AGENT_TIMEOUT=60
MAX_CONCURRENT_TASKS=5
RETRY_MAX_ATTEMPTS=3
```

## Step 8: Run Your First Project

### Test the Application

```bash
# Run the code review assistant
python main.py https://github.com/octocat/Hello-World README.md main.py

# Expected output:
# ✅ All agents registered successfully
# 🚀 Starting code review for: https://github.com/octocat/Hello-World
# 📥 Stage 1: Fetching code files...
#   ✅ Fetched: README.md
#   ✅ Fetched: main.py
# 🔍 Stage 2: Analyzing code quality...
#   ✅ Analyzed: README.md (Quality: 95/100)
#   ✅ Analyzed: main.py (Quality: 88/100)
# 📊 Stage 3: Generating report...
# ✅ Code review completed successfully!
```

### Example Output

```
==================================================
📋 CODE REVIEW SUMMARY
==================================================
Overall Quality: Good
Quality Score: 91.5/100
Files Analyzed: 2
Critical Issues: 0
Warnings: 1
Suggestions: 2

📁 Report saved to: code_review_report_20240715_143022.json

💡 RECOMMENDATIONS:
📏 Consider setting up automatic line length formatting
✅ Create issues for TODO comments to track pending work

🎉 Your first LeanVibe Agent project is complete!
```

## Step 9: Understanding What You Built

### Agent Architecture

1. **Scraper Agent** (`github-scraper`)
   - Fetches code from GitHub repositories
   - Handles API requests and content parsing
   - Provides error handling for missing files

2. **Analyzer Agent** (`code-analyzer`) 
   - Analyzes code quality and style
   - Detects syntax errors and issues
   - Generates quality scores and recommendations

3. **Reporter Agent** (`report-generator`)
   - Aggregates analysis results
   - Creates comprehensive reports
   - Generates actionable recommendations

4. **Coordinator** (MultiAgentCoordinator)
   - Orchestrates the workflow pipeline
   - Manages agent communication
   - Handles error recovery and retries

### Workflow Pipeline

```
GitHub Repo → Scraper Agent → Code Content
                    ↓
Code Content → Analyzer Agent → Quality Analysis
                    ↓  
Quality Analysis → Reporter Agent → Final Report
```

## Step 10: Next Steps

### Extend Your Project

**Add More Agents:**
```python
# Security scanner agent
class SecurityScannerAgent(Agent):
    async def process_task(self, task: Task) -> dict:
        # Scan for security vulnerabilities
        pass

# Performance analyzer agent  
class PerformanceAnalyzerAgent(Agent):
    async def process_task(self, task: Task) -> dict:
        # Analyze performance patterns
        pass
```

**Improve Analysis:**
- Add more sophisticated code quality checks
- Integrate with external tools (pylint, flake8)
- Add language-specific analyzers
- Include test coverage analysis

**Enhanced Reporting:**
- Generate HTML reports with charts
- Email report delivery
- Integration with issue tracking systems
- Historical quality trend analysis

### Learn More

1. **Advanced Coordination**: [Multi-Agent Coordination Guide](../MULTIAGENT_COORDINATOR_ARCHITECTURE.md)
2. **Configuration**: [Configuration Guide](../guides/configuration.md)
3. **Deployment**: [Deployment Guide](../guides/deployment.md)
4. **Real Project**: [Medium Clone Tutorial](../../tutorials/MEDIUM_CLONE_TUTORIAL.md)

## Troubleshooting

### Common Issues

**Agent Registration Failed**
```python
# Check agent creation
agent = create_scraper()
print(f"Agent ID: {agent.agent_id}, Type: {agent.agent_type}")
```

**GitHub API Rate Limits**
```bash
# Add GitHub token to .env
GITHUB_TOKEN=your_token_here
```

**Task Execution Errors**
```python
# Add more detailed error logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Congratulations! 🎉

You've successfully built your first multi-agent system with LeanVibe Agent Hive! You now understand:

- How to create specialized agents
- How to coordinate multi-agent workflows
- How to handle errors and async operations
- How to generate reports and summaries

**Ready for more?** Try the [Medium Clone Tutorial](../../tutorials/MEDIUM_CLONE_TUTORIAL.md) to build a complete web application with agent-driven development.

---

*Welcome to the world of autonomous agent development!* 🚀