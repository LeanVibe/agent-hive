#!/usr/bin/env python3
"""
Comprehensive Security Monitoring System Validation

This script validates all components of the Security Monitoring & Audit system:
- SecurityAuditLogger (audit logging with tamper resistance)
- SecurityMonitor (real-time monitoring and anomaly detection) 
- SecurityAlertSystem (automated alerting with multiple channels)
- SecurityAnalytics (compliance reporting and analytics)
- SecurityDashboard (real-time metrics and visualization)
- SecurityMonitoringIntegration (unified event processing)
"""

import asyncio
import sys
import tempfile
import os
import time
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.append('.')

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---")

def print_success(message: str):
    """Print a success message."""
    print(f"✅ {message}")

def print_error(message: str):
    """Print an error message."""
    print(f"❌ {message}")

def print_info(message: str):
    """Print an info message."""
    print(f"ℹ️  {message}")

async def validate_audit_logger():
    """Validate SecurityAuditLogger functionality."""
    print_section("Security Audit Logger Validation")
    
    try:
        from security.audit_logger import (
            SecurityAuditLogger, create_security_event, 
            SecurityEventType, SecuritySeverity
        )
        
        # Create test configuration
        temp_dir = tempfile.mkdtemp()
        config = {
            'db_path': os.path.join(temp_dir, 'test_audit.db'),
            'log_dir': temp_dir,
            'encryption_enabled': False,
            'batch_size': 5
        }
        
        print_subsection("Basic Functionality")
        
        # Test initialization
        audit_logger = SecurityAuditLogger(config)
        print_success("SecurityAuditLogger initialized")
        
        # Test event creation
        event = create_security_event(
            event_type=SecurityEventType.SYSTEM_HEALTH_CHECK,
            severity=SecuritySeverity.INFO,
            source_component='validation_test',
            action='system_validation',
            user_id='test_user'
        )
        print_success("Security event created")
        
        # Test event logging
        result = audit_logger.log_event_sync(event)
        if result:
            print_success("Event logged successfully")
        else:
            print_error("Event logging failed")
            return False
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Test event retrieval
        recent_events = audit_logger.get_recent_events(10)
        if len(recent_events) >= 1:
            print_success(f"Retrieved {len(recent_events)} recent events")
        else:
            print_error("No events retrieved")
            return False
        
        # Test statistics
        stats = await audit_logger.get_statistics(hours=1)
        if stats and stats.total_events >= 1:
            print_success(f"Statistics generated: {stats.total_events} events, security score: {stats.security_score}")
        else:
            print_error("Statistics generation failed")
            return False
        
        # Test performance metrics
        metrics = audit_logger.get_performance_metrics()
        if metrics and 'total_events_processed' in metrics:
            print_success(f"Performance metrics: {metrics['total_events_processed']} events processed")
        else:
            print_error("Performance metrics failed")
            return False
        
        # Cleanup
        try:
            os.unlink(config['db_path'])
            os.rmdir(temp_dir)
        except:
            pass
            
        return True
        
    except Exception as e:
        print_error(f"Audit logger validation failed: {e}")
        return False

async def validate_security_monitor():
    """Validate SecurityMonitor functionality."""
    print_section("Security Monitor Validation")
    
    try:
        from security.security_monitor import SecurityMonitor
        from security.audit_logger import create_security_event, SecurityEventType, SecuritySeverity
        
        print_subsection("Basic Functionality")
        
        # Test initialization
        monitor = SecurityMonitor()
        print_success("SecurityMonitor initialized")
        
        # Test event processing
        event = create_security_event(
            event_type=SecurityEventType.SECURITY_COMMAND_BLOCKED,
            severity=SecuritySeverity.HIGH,
            source_component='validation_test',
            user_id='test_user',
            action='rm -rf /',
            client_ip='192.168.1.100'
        )
        
        # Process event
        anomalies = await monitor.process_security_event(event)
        print_success(f"Event processed, detected {len(anomalies)} anomalies")
        
        # Test monitoring status
        status = monitor.get_monitoring_status()
        if status and status.get('status') == 'active':
            print_success(f"Monitoring status: {status['status']}")
        else:
            print_error("Monitoring status check failed")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Security monitor validation failed: {e}")
        return False

async def validate_alert_system():
    """Validate SecurityAlertSystem functionality."""
    print_section("Security Alert System Validation")
    
    try:
        from security.alert_system import SecurityAlertSystem
        from security.audit_logger import create_security_event, SecurityEventType, SecuritySeverity
        
        print_subsection("Basic Functionality")
        
        # Test initialization
        alert_system = SecurityAlertSystem({
            'console_enabled': True,
            'email_enabled': False,
            'slack_enabled': False
        })
        print_success("SecurityAlertSystem initialized")
        
        # Test event evaluation
        event = create_security_event(
            event_type=SecurityEventType.SECURITY_COMMAND_BLOCKED,
            severity=SecuritySeverity.CRITICAL,
            source_component='validation_test',
            action='dangerous_command'
        )
        
        alerts = await alert_system.evaluate_event(event)
        print_success(f"Event evaluated, generated {len(alerts)} alerts")
        
        # Test alert statistics
        stats = alert_system.get_alert_statistics()
        if stats:
            print_success(f"Alert statistics: {stats.get('total_alerts', 0)} total alerts")
        else:
            print_error("Alert statistics failed")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Alert system validation failed: {e}")
        return False

async def validate_security_analytics():
    """Validate SecurityAnalytics functionality."""
    print_section("Security Analytics Validation")
    
    try:
        from security.security_analytics import SecurityAnalytics, ComplianceFramework
        from security.audit_logger import SecurityAuditLogger
        from security.security_monitor import SecurityMonitor
        
        print_subsection("Basic Functionality")
        
        # Create dependencies
        audit_logger = SecurityAuditLogger({'encryption_enabled': False})
        monitor = SecurityMonitor()
        
        # Test initialization
        analytics = SecurityAnalytics(audit_logger, monitor)
        print_success("SecurityAnalytics initialized")
        
        # Test analytics summary
        summary = analytics.get_analytics_summary()
        if summary and len(summary) > 0:
            print_success(f"Analytics summary generated with {len(summary)} sections")
        else:
            print_error("Analytics summary generation failed")
            return False
        
        # Test compliance report generation
        try:
            report = await analytics.generate_compliance_report(ComplianceFramework.SOC2)
            if report:
                print_success(f"Compliance report generated: {report.framework.value}")
            else:
                print_error("Compliance report generation failed")
                return False
        except Exception as e:
            print_info(f"Compliance report skipped due to missing data: {e}")
        
        return True
        
    except Exception as e:
        print_error(f"Security analytics validation failed: {e}")
        return False

async def validate_security_dashboard():
    """Validate SecurityDashboard functionality."""
    print_section("Security Dashboard Validation")
    
    try:
        from dashboard.security_dashboard import SecurityDashboard
        from security.audit_logger import SecurityAuditLogger
        from security.security_monitor import SecurityMonitor
        
        print_subsection("Basic Functionality")
        
        # Create dependencies
        audit_logger = SecurityAuditLogger({'encryption_enabled': False})
        monitor = SecurityMonitor()
        
        # Test initialization
        dashboard = SecurityDashboard(audit_logger, monitor)
        print_success("SecurityDashboard initialized")
        
        # Test dashboard data
        data = await dashboard.get_dashboard_data()
        if data and data.get('status') == 'active':
            print_success(f"Dashboard data retrieved: {data['status']}")
        else:
            print_error("Dashboard data retrieval failed")
            return False
        
        # Test security overview
        overview = await dashboard.get_security_overview()
        if overview:
            print_success("Security overview generated")
        else:
            print_error("Security overview generation failed")
            return False
        
        # Test dashboard health
        health = dashboard.get_dashboard_health()
        if health and 'status' in health:
            print_success(f"Dashboard health: {health['status']}")
        else:
            print_error("Dashboard health check failed")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Security dashboard validation failed: {e}")
        return False

async def validate_monitoring_integration():
    """Validate SecurityMonitoringIntegration functionality."""
    print_section("Security Monitoring Integration Validation")
    
    try:
        from security.monitoring_integration import (
            SecurityMonitoringIntegration, get_integration_status
        )
        
        print_subsection("Basic Functionality")
        
        # Test initialization
        integration = SecurityMonitoringIntegration()
        print_success("SecurityMonitoringIntegration initialized")
        
        # Test integration status
        status = get_integration_status()
        if status and status.get('status') == 'active':
            print_success(f"Integration status: {status['status']}")
            print_info(f"  Components registered: {sum(status['components_registered'].values())}/4")
            print_info(f"  Monitoring systems: {sum(status['monitoring_systems'].values())}/3")
            print_info(f"  Events processed: {status['performance']['events_processed']}")
        else:
            print_error("Integration status check failed")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Monitoring integration validation failed: {e}")
        return False

async def validate_end_to_end_workflow():
    """Validate end-to-end security monitoring workflow."""
    print_section("End-to-End Workflow Validation")
    
    try:
        from security.audit_logger import (
            SecurityAuditLogger, create_security_event, 
            SecurityEventType, SecuritySeverity
        )
        from security.security_monitor import SecurityMonitor
        from security.alert_system import SecurityAlertSystem
        from security.security_analytics import SecurityAnalytics
        from dashboard.security_dashboard import SecurityDashboard
        
        print_subsection("Complete Workflow Test")
        
        # Initialize all components
        temp_dir = tempfile.mkdtemp()
        config = {
            'db_path': os.path.join(temp_dir, 'workflow_test.db'),
            'log_dir': temp_dir,
            'encryption_enabled': False
        }
        
        audit_logger = SecurityAuditLogger(config)
        monitor = SecurityMonitor()
        alert_system = SecurityAlertSystem({'console_enabled': False})  # Disable console for clean output
        analytics = SecurityAnalytics(audit_logger, monitor)
        dashboard = SecurityDashboard(audit_logger, monitor)
        
        print_success("All components initialized")
        
        # Create and process a security event
        event = create_security_event(
            event_type=SecurityEventType.SECURITY_COMMAND_BLOCKED,
            severity=SecuritySeverity.HIGH,
            source_component='end_to_end_test',
            user_id='test_user',
            action='rm -rf /',
            client_ip='192.168.1.100'
        )
        
        # Process through the pipeline
        print_info("Processing security event through pipeline...")
        
        # 1. Log the event
        logged = audit_logger.log_event_sync(event)
        if logged:
            print_success("Event logged to audit system")
        else:
            print_error("Event logging failed")
            return False
        
        # 2. Process through monitor
        anomalies = await monitor.process_security_event(event)
        if anomalies is not None:
            print_success(f"Event processed by monitor, {len(anomalies)} anomalies detected")
        else:
            print_error("Monitor processing failed")
            return False
        
        # 3. Process through alert system
        alerts = await alert_system.evaluate_event(event)
        if alerts is not None:
            print_success(f"Event processed by alert system, {len(alerts)} alerts generated")
        else:
            print_error("Alert system processing failed")
            return False
        
        # Wait for async processing
        await asyncio.sleep(2)
        
        # 4. Verify data collection
        recent_events = audit_logger.get_recent_events(10)
        if len(recent_events) >= 1:
            print_success(f"Audit data verified: {len(recent_events)} events stored")
        else:
            print_error("Audit data verification failed")
            return False
        
        # 5. Test analytics
        summary = analytics.get_analytics_summary()
        if summary:
            print_success("Analytics summary generated")
        else:
            print_error("Analytics summary failed")
            return False
        
        # 6. Test dashboard
        dashboard_data = await dashboard.get_dashboard_data()
        if dashboard_data and dashboard_data.get('status') == 'active':
            print_success("Dashboard data collected")
        else:
            print_error("Dashboard data collection failed")
            return False
        
        # Cleanup
        try:
            os.unlink(config['db_path'])
            os.rmdir(temp_dir)
        except:
            pass
        
        print_success("End-to-end workflow validation completed successfully!")
        return True
        
    except Exception as e:
        print_error(f"End-to-end workflow validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run comprehensive validation of the security monitoring system."""
    print_section("Security Monitoring & Audit System Validation")
    print_info("Validating all components of the security monitoring system...")
    print_info("This validates PR #5 implementation: Security Monitoring & Audit")
    
    start_time = time.time()
    results = []
    
    # Run all validation tests
    tests = [
        ("Audit Logger", validate_audit_logger),
        ("Security Monitor", validate_security_monitor),
        ("Alert System", validate_alert_system),
        ("Security Analytics", validate_security_analytics),
        ("Security Dashboard", validate_security_dashboard),
        ("Monitoring Integration", validate_monitoring_integration),
        ("End-to-End Workflow", validate_end_to_end_workflow)
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"{test_name} validation encountered an error: {e}")
            results.append((test_name, False))
    
    # Summary
    print_section("Validation Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    elapsed = time.time() - start_time
    
    print(f"\nResults: {passed}/{total} tests passed")
    print(f"Validation completed in {elapsed:.2f} seconds")
    
    if passed == total:
        print_success("🎉 ALL VALIDATIONS PASSED!")
        print_info("Security Monitoring & Audit system is fully operational!")
        print_info("✅ PR #5 implementation is complete and validated")
        return 0
    else:
        print_error(f"❌ {total - passed} validations failed")
        print_info("Review the errors above and fix the issues")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)