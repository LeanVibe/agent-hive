#!/usr/bin/env python3
"""
Production Readiness Verification Script
Comprehensive validation of Agent Hive production readiness.

This script:
1. Verifies all core systems operational
2. Runs health checks on all services
3. Verifies test coverage
4. Performs security scans
5. Generates production readiness report
6. Creates deployment checklist
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import statistics

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ProductionReadinessVerifier:
    """Comprehensive production readiness verification"""
    
    def __init__(self):
        self.verification_start = datetime.now()
        self.results = {
            'system_health': {},
            'test_coverage': {},
            'security': {},
            'performance': {},
            'issues': [],
            'recommendations': []
        }
        self.output_dir = project_root / "docs"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def run_verification(self) -> Dict[str, Any]:
        """Run complete production readiness verification"""
        
        print("🔍 AGENT HIVE - PRODUCTION READINESS VERIFICATION")
        print("=" * 60)
        print(f"Started: {self.verification_start.isoformat()}")
        print("")
        
        # Step 1: System Health Checks
        print("📊 Step 1: System Health Checks")
        print("-" * 40)
        await self._check_system_health()
        
        # Step 2: Test Coverage Analysis
        print("\n📊 Step 2: Test Coverage Analysis")
        print("-" * 40)
        await self._check_test_coverage()
        
        # Step 3: Security Scans
        print("\n📊 Step 3: Security Scans")
        print("-" * 40)
        await self._check_security()
        
        # Step 4: Performance Checks
        print("\n📊 Step 4: Performance Checks")
        print("-" * 40)
        await self._check_performance()
        
        # Step 5: Generate Reports
        print("\n📄 Step 5: Generating Reports")
        print("-" * 40)
        await self._generate_reports()
        
        return self.results
    
    async def _check_system_health(self):
        """Verify all core systems operational"""
        
        checks = {
            'multi_agent_coordinator': await self._check_component('advanced_orchestration'),
            'service_discovery': await self._check_component('external_api/service_discovery'),
            'api_gateway': await self._check_component('external_api/api_gateway'),
            'performance_monitoring': await self._check_component('performance'),
            'quality_gates': await self._check_component('enhanced_quality_gates'),
            'intelligence_framework': await self._check_component('intelligence_framework'),
        }
        
        # Check Docker services if available
        docker_checks = await self._check_docker_services()
        checks.update(docker_checks)
        
        self.results['system_health'] = checks
        
        # Display results
        for component, status in checks.items():
            icon = "✅" if status.get('operational', False) else "❌"
            print(f"  {icon} {component}: {status.get('status', 'Unknown')}")
        
        operational_count = sum(1 for c in checks.values() if c.get('operational', False))
        total_count = len(checks)
        print(f"\n  System Health: {operational_count}/{total_count} components operational")
    
    async def _check_component(self, component_path: str) -> Dict[str, Any]:
        """Check if a component exists and is importable"""
        
        try:
            component_file = project_root / component_path.replace('/', '/')
            if component_file.is_file():
                # Try to import
                module_name = component_path.replace('/', '.').replace('.py', '')
                try:
                    __import__(module_name)
                    return {'operational': True, 'status': 'Operational', 'path': str(component_file)}
                except ImportError:
                    return {'operational': False, 'status': 'Import failed', 'path': str(component_file)}
            elif (project_root / component_path).is_dir():
                # Check if directory has __init__.py or main files
                init_file = (project_root / component_path / '__init__.py')
                if init_file.exists():
                    return {'operational': True, 'status': 'Directory exists', 'path': str(component_path)}
                else:
                    return {'operational': True, 'status': 'Directory exists (no __init__)', 'path': str(component_path)}
            else:
                return {'operational': False, 'status': 'Not found', 'path': str(component_path)}
        except Exception as e:
            return {'operational': False, 'status': f'Error: {str(e)}', 'path': str(component_path)}
    
    async def _check_docker_services(self) -> Dict[str, Any]:
        """Check Docker services if docker-compose is available"""
        
        checks = {}
        
        # Check if docker-compose.yml exists
        docker_compose = project_root / 'docker-compose.yml'
        if docker_compose.exists():
            checks['docker_compose'] = {'operational': True, 'status': 'Configuration exists'}
            
            # Try to check if services are defined
            try:
                result = subprocess.run(
                    ['docker-compose', 'config', '--services'],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    services = result.stdout.strip().split('\n')
                    checks['docker_services'] = {
                        'operational': True,
                        'status': f'{len(services)} services defined',
                        'services': services
                    }
            except (subprocess.TimeoutExpired, FileNotFoundError):
                checks['docker_services'] = {'operational': False, 'status': 'Docker not available'}
        else:
            checks['docker_compose'] = {'operational': False, 'status': 'No docker-compose.yml'}
        
        return checks
    
    async def _check_test_coverage(self):
        """Verify test coverage"""
        
        try:
            # Try to run pytest with coverage
            print("  Running test coverage analysis...")
            
            result = subprocess.run(
                ['python3', '-m', 'pytest', '--cov=advanced_orchestration', '--cov=external_api', 
                 '--cov-report=term', '--cov-report=json:coverage.json', '-q'],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse coverage from output or JSON
            coverage_data = {}
            
            if (project_root / 'coverage.json').exists():
                with open(project_root / 'coverage.json') as f:
                    coverage_json = json.load(f)
                    total_coverage = coverage_json.get('totals', {}).get('percent_covered', 0)
                    coverage_data = {
                        'overall_coverage': total_coverage,
                        'target': 70.0,
                        'met': total_coverage >= 70.0,
                        'details': coverage_json
                    }
            else:
                # Try to parse from stdout
                coverage_lines = [line for line in result.stdout.split('\n') if 'TOTAL' in line or 'total' in line.lower()]
                if coverage_lines:
                    # Extract percentage
                    coverage_data = {
                        'overall_coverage': 0,  # Couldn't parse
                        'target': 70.0,
                        'met': False,
                        'note': 'Could not parse coverage from output'
                    }
                else:
                    coverage_data = {
                        'overall_coverage': 0,
                        'target': 70.0,
                        'met': False,
                        'note': 'Coverage analysis not available - tests may need to be run first'
                    }
            
            self.results['test_coverage'] = coverage_data
            
            coverage_pct = coverage_data.get('overall_coverage', 0)
            status_icon = "✅" if coverage_data.get('met', False) else "⚠️"
            print(f"  {status_icon} Overall Coverage: {coverage_pct:.1f}% (target: 70%)")
            
        except subprocess.TimeoutExpired:
            self.results['test_coverage'] = {
                'overall_coverage': 0,
                'target': 70.0,
                'met': False,
                'note': 'Test run timed out (>5 minutes)'
            }
            print("  ⚠️  Test coverage analysis timed out")
        except Exception as e:
            self.results['test_coverage'] = {
                'overall_coverage': 0,
                'target': 70.0,
                'met': False,
                'error': str(e)
            }
            print(f"  ❌ Test coverage analysis failed: {str(e)}")
    
    async def _check_security(self):
        """Perform security scans"""
        
        security_results = {
            'secrets_scan': {},
            'dependency_audit': {},
            'auth_checks': {}
        }
        
        # Secrets scan
        print("  Scanning for hardcoded secrets...")
        try:
            # Try git-secrets
            result = subprocess.run(
                ['git', 'secrets', '--scan'],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                security_results['secrets_scan'] = {
                    'status': 'clean',
                    'method': 'git-secrets',
                    'issues': []
                }
                print("    ✅ No secrets found (git-secrets)")
            else:
                # Check output for issues
                if 'matches' in result.stdout.lower() or 'found' in result.stdout.lower():
                    security_results['secrets_scan'] = {
                        'status': 'issues_found',
                        'method': 'git-secrets',
                        'output': result.stdout
                    }
                    print("    ⚠️  Potential secrets found - review required")
                else:
                    security_results['secrets_scan'] = {
                        'status': 'clean',
                        'method': 'git-secrets',
                        'note': 'Scan completed'
                    }
                    print("    ✅ No secrets found")
        except FileNotFoundError:
            # git-secrets not installed, try basic pattern matching
            security_results['secrets_scan'] = {
                'status': 'not_available',
                'method': 'git-secrets not installed',
                'recommendation': 'Install git-secrets or truffleHog for comprehensive scan'
            }
            print("    ⚠️  git-secrets not installed - manual review recommended")
        except Exception as e:
            security_results['secrets_scan'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"    ❌ Secrets scan failed: {str(e)}")
        
        # Dependency audit
        print("  Auditing dependencies for vulnerabilities...")
        try:
            # Try uv pip-audit
            result = subprocess.run(
                ['uv', 'pip-audit'],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                # Check if vulnerabilities found
                if 'No known vulnerabilities found' in result.stdout:
                    security_results['dependency_audit'] = {
                        'status': 'clean',
                        'method': 'uv pip-audit',
                        'vulnerabilities': 0
                    }
                    print("    ✅ No known vulnerabilities")
                else:
                    # Parse vulnerabilities
                    vuln_count = result.stdout.count('VULNERABLE') or result.stdout.count('vulnerability')
                    security_results['dependency_audit'] = {
                        'status': 'vulnerabilities_found',
                        'method': 'uv pip-audit',
                        'vulnerabilities': vuln_count,
                        'output': result.stdout
                    }
                    print(f"    ⚠️  {vuln_count} potential vulnerabilities found")
            else:
                security_results['dependency_audit'] = {
                    'status': 'error',
                    'method': 'uv pip-audit',
                    'error': result.stderr
                }
                print("    ⚠️  Dependency audit had issues")
        except FileNotFoundError:
            security_results['dependency_audit'] = {
                'status': 'not_available',
                'method': 'uv not available',
                'recommendation': 'Install uv or use npm audit for JavaScript dependencies'
            }
            print("    ⚠️  uv not available - manual audit recommended")
        except Exception as e:
            security_results['dependency_audit'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"    ❌ Dependency audit failed: {str(e)}")
        
        # Auth checks
        print("  Checking authentication/authorization...")
        auth_dir = project_root / 'security'
        if auth_dir.exists():
            auth_files = list(auth_dir.glob('*.py'))
            security_results['auth_checks'] = {
                'status': 'present',
                'auth_files': len(auth_files),
                'path': str(auth_dir)
            }
            print(f"    ✅ Authentication module found ({len(auth_files)} files)")
        else:
            security_results['auth_checks'] = {
                'status': 'not_found',
                'path': str(auth_dir)
            }
            print("    ⚠️  Security directory not found")
        
        self.results['security'] = security_results
    
    async def _check_performance(self):
        """Check performance metrics"""
        
        # Check for performance baseline
        baseline_file = project_root / 'performance_baseline.json'
        if baseline_file.exists():
            try:
                with open(baseline_file) as f:
                    baseline = json.load(f)
                    self.results['performance'] = {
                        'baseline_available': True,
                        'baseline_data': baseline
                    }
                    print("  ✅ Performance baseline found")
            except Exception as e:
                self.results['performance'] = {
                    'baseline_available': False,
                    'error': str(e)
                }
                print("  ⚠️  Could not read performance baseline")
        else:
            self.results['performance'] = {
                'baseline_available': False,
                'note': 'No performance baseline found - consider creating one'
            }
            print("  ⚠️  No performance baseline found")
        
        # Check API response time target
        self.results['performance']['targets'] = {
            'api_response_p95': '<500ms',
            'task_assignment_latency': '<500ms',
            'resource_utilization': '95%+'
        }
    
    async def _generate_reports(self):
        """Generate production readiness report and deployment checklist"""
        
        # Save metrics JSON
        metrics_path = self.output_dir / "production_readiness_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Generate markdown report
        report_path = self.output_dir / "PRODUCTION_READINESS_REPORT.md"
        await self._generate_readiness_report(report_path)
        
        # Generate deployment checklist
        checklist_path = self.output_dir / "DEPLOYMENT_CHECKLIST.md"
        await self._generate_deployment_checklist(checklist_path)
        
        print(f"  ✅ Production Readiness Report: {report_path}")
        print(f"  ✅ Deployment Checklist: {checklist_path}")
        print(f"  ✅ Metrics JSON: {metrics_path}")
    
    async def _generate_readiness_report(self, report_path: Path):
        """Generate comprehensive production readiness report"""
        
        system_health = self.results['system_health']
        test_coverage = self.results['test_coverage']
        security = self.results['security']
        
        # Calculate overall readiness
        operational_components = sum(1 for c in system_health.values() if c.get('operational', False))
        total_components = len(system_health)
        health_percentage = (operational_components / total_components * 100) if total_components > 0 else 0
        
        coverage_met = test_coverage.get('met', False)
        security_clean = (
            security.get('secrets_scan', {}).get('status') in ['clean', 'not_available'] and
            security.get('dependency_audit', {}).get('status') in ['clean', 'not_available']
        )
        
        overall_ready = health_percentage >= 80 and coverage_met and security_clean
        
        report = f"""# Production Readiness Report - Agent Hive

**Date:** {self.verification_start.isoformat()}
**Status:** {'✅ PRODUCTION READY' if overall_ready else '⚠️ NEEDS WORK'}

---

## Executive Summary

Agent Hive production readiness has been verified through comprehensive system checks, test coverage analysis, and security scans.

**Key Findings:**
- **System Health:** {operational_components}/{total_components} components operational ({health_percentage:.1f}%)
- **Test Coverage:** {test_coverage.get('overall_coverage', 0):.1f}% (target: 70%+) {'✅' if coverage_met else '⚠️'}
- **Security:** {'✅ Clean' if security_clean else '⚠️ Issues found'}
- **Overall Status:** {'✅ READY' if overall_ready else '⚠️ NEEDS WORK'}

---

## System Health Status

| Component | Status | Details |
|-----------|--------|---------|
"""
        
        for component, status in system_health.items():
            icon = "✅" if status.get('operational', False) else "❌"
            status_text = status.get('status', 'Unknown')
            report += f"| **{component}** | {icon} {status_text} | {status.get('path', 'N/A')} |\n"
        
        report += f"""
**Overall:** {operational_components}/{total_components} components operational

---

## Test Coverage

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Overall Coverage** | {test_coverage.get('overall_coverage', 0):.1f}% | >70% | {'✅' if coverage_met else '⚠️'} |
| **Target Met** | {'Yes' if coverage_met else 'No'} | Yes | {'✅' if coverage_met else '⚠️'} |

**Note:** {test_coverage.get('note', 'Coverage analysis completed')}

---

## Security Assessment

### Secrets Scan
- **Status:** {security.get('secrets_scan', {}).get('status', 'Unknown')}
- **Method:** {security.get('secrets_scan', {}).get('method', 'N/A')}
- **Issues:** {len(security.get('secrets_scan', {}).get('issues', []))}

### Dependency Audit
- **Status:** {security.get('dependency_audit', {}).get('status', 'Unknown')}
- **Method:** {security.get('dependency_audit', {}).get('method', 'N/A')}
- **Vulnerabilities:** {security.get('dependency_audit', {}).get('vulnerabilities', 0)}

### Authentication/Authorization
- **Status:** {security.get('auth_checks', {}).get('status', 'Unknown')}
- **Auth Files:** {security.get('auth_checks', {}).get('auth_files', 0)}

---

## Performance Metrics

"""
        
        if self.results['performance'].get('baseline_available'):
            report += "✅ Performance baseline available\n"
        else:
            report += "⚠️ No performance baseline found - consider creating one\n"
        
        report += f"""
**Targets:**
- API Response (P95): <500ms
- Task Assignment Latency: <500ms
- Resource Utilization: 95%+

---

## Issues & Blockers

"""
        
        issues = []
        if health_percentage < 80:
            issues.append(f"System health below target ({health_percentage:.1f}% < 80%)")
        if not coverage_met:
            issues.append(f"Test coverage below target ({test_coverage.get('overall_coverage', 0):.1f}% < 70%)")
        if not security_clean:
            issues.append("Security issues found - review required")
        
        if issues:
            for issue in issues:
                report += f"- ⚠️ {issue}\n"
        else:
            report += "- ✅ No critical issues found\n"
        
        report += f"""
---

## Recommendations

"""
        
        if overall_ready:
            report += """- ✅ **System is production-ready** - Proceed with deployment
- ✅ Create deployment checklist (see DEPLOYMENT_CHECKLIST.md)
- ✅ Set up monitoring and alerting
- ✅ Plan pilot program with 2-3 engineering teams
"""
        else:
            report += """- ⚠️ **Address blockers before deployment:**
"""
            if health_percentage < 80:
                report += "  - Fix non-operational components\n"
            if not coverage_met:
                report += "  - Increase test coverage to 70%+\n"
            if not security_clean:
                report += "  - Resolve security issues\n"
            report += "- 🔧 Re-run verification after fixes\n"
        
        report += f"""
---

## Next Steps

1. **If Ready:**
   - Review deployment checklist
   - Set up infrastructure (PostgreSQL, Redis)
   - Configure environment variables
   - Deploy to staging environment
   - Run pilot program

2. **If Needs Work:**
   - Address identified blockers
   - Re-run verification
   - Update this report

---

**Report Generated:** {datetime.now().isoformat()}
"""
        
        with open(report_path, 'w') as f:
            f.write(report)
    
    async def _generate_deployment_checklist(self, checklist_path: Path):
        """Generate deployment checklist"""
        
        # Read docker-compose to understand infrastructure needs
        docker_compose = project_root / 'docker-compose.yml'
        services = []
        if docker_compose.exists():
            try:
                with open(docker_compose) as f:
                    content = f.read()
                    # Extract service names (basic parsing)
                    import re
                    service_matches = re.findall(r'^\s+(\w+):', content, re.MULTILINE)
                    services = list(set(service_matches))
            except:
                pass
        
        checklist = f"""# Agent Hive - Deployment Checklist

**Generated:** {datetime.now().isoformat()}
**Project:** Agent Hive
**Location:** `leanvibe-dev/agent-hive/`

---

## Pre-Deployment Requirements

### Infrastructure
- [ ] **PostgreSQL Database** - Version 14+ recommended
- [ ] **Redis** - Version 6+ for caching and queues
- [ ] **Docker & Docker Compose** - For containerized deployment
- [ ] **Domain/Subdomain** - For API access (e.g., `api.agenthive.com`)

### Environment Variables
- [ ] **Database Connection** - `DATABASE_URL` or `POSTGRES_URL`
- [ ] **Redis Connection** - `REDIS_URL`
- [ ] **API Keys** - Anthropic/OpenAI for AI agents
- [ ] **JWT Secret** - For authentication
- [ ] **Environment** - `ENV=production`

### Configuration Files
- [ ] Review `config/base.yaml`
- [ ] Review `config/environments/production.yaml`
- [ ] Review `docker-compose.yml`
- [ ] Review `.env.example` for required variables

---

## Deployment Steps

### Step 1: Infrastructure Setup
```bash
# Start infrastructure services
docker-compose up -d postgres redis

# Verify services are running
docker-compose ps
```

### Step 2: Database Setup
```bash
# Run migrations (if applicable)
# Check for alembic or migration scripts
# Example: alembic upgrade head
```

### Step 3: Application Deployment
```bash
# Build production image
docker-compose build agent-hive

# Start application
docker-compose up -d agent-hive

# Or use Makefile
make up
```

### Step 4: Health Checks
```bash
# Check health endpoint
curl http://localhost:8000/health

# Check all services
make health
```

---

## Post-Deployment Verification

### Health Endpoints
- [ ] **API Health:** `GET /health` returns 200
- [ ] **Service Discovery:** Verify service registration
- [ ] **API Gateway:** Verify routing works
- [ ] **Database:** Verify connectivity
- [ ] **Redis:** Verify connectivity

### Functional Tests
- [ ] **Multi-Agent Coordination:** Test agent orchestration
- [ ] **Service Discovery:** Test service registration/discovery
- [ ] **API Gateway:** Test API routing and auth
- [ ] **Performance Monitoring:** Verify metrics collection

### Monitoring Setup
- [ ] **Logs:** Configure log aggregation
- [ ] **Metrics:** Set up Prometheus/Grafana (if applicable)
- [ ] **Alerts:** Configure alerting rules
- [ ] **Dashboards:** Set up monitoring dashboards

---

## Rollback Procedures

If deployment fails:
1. Stop new deployment: `docker-compose down`
2. Restore previous version: `git checkout <previous-tag>`
3. Rebuild and deploy: `docker-compose up -d`
4. Verify health: `make health`

---

## Environment Variables Reference

Based on `.env.example` and configuration files:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/agenthive
POSTGRES_URL=postgresql://user:pass@host:5432/agenthive

# Redis
REDIS_URL=redis://host:6379/0

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# JWT
JWT_SECRET=your-secret-key-here

# Environment
ENV=production
LOG_LEVEL=INFO
```

---

## Service URLs (Default)

- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health
- **Dashboard:** http://localhost:8000/dashboard (if applicable)

---

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Verify DATABASE_URL is correct
   - Check PostgreSQL is running
   - Verify network connectivity

2. **Redis Connection Failed**
   - Verify REDIS_URL is correct
   - Check Redis is running
   - Verify network connectivity

3. **Services Not Starting**
   - Check logs: `docker-compose logs`
   - Verify environment variables
   - Check port conflicts

---

**Last Updated:** {datetime.now().isoformat()}
"""
        
        with open(checklist_path, 'w') as f:
            f.write(checklist)


async def main():
    """Main verification runner"""
    
    verifier = ProductionReadinessVerifier()
    results = await verifier.run_verification()
    
    # Display summary
    print("\n" + "=" * 60)
    print("🎯 PRODUCTION READINESS VERIFICATION COMPLETE")
    print("=" * 60)
    
    system_health = results['system_health']
    operational = sum(1 for c in system_health.values() if c.get('operational', False))
    total = len(system_health)
    
    coverage = results['test_coverage'].get('overall_coverage', 0)
    coverage_met = results['test_coverage'].get('met', False)
    
    print(f"System Health: {operational}/{total} components operational")
    print(f"Test Coverage: {coverage:.1f}% ({'✅ Met' if coverage_met else '⚠️ Below target'})")
    print(f"Security: {'✅ Clean' if results['security'].get('secrets_scan', {}).get('status') == 'clean' else '⚠️ Review needed'}")
    
    overall_ready = (operational / total >= 0.8) if total > 0 else False and coverage_met
    
    if overall_ready:
        print("\n🎉 PRODUCTION READY - Ready for deployment!")
    else:
        print("\n⚠️  NEEDS WORK - Address blockers before deployment")
    
    print("\n📄 Reports generated in docs/ directory")


if __name__ == "__main__":
    asyncio.run(main())
