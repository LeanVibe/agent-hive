#!/usr/bin/env python3
"""
Test script for Enhanced Context Monitor
Validates all functionality with various scenarios
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / ".claude" / "scripts"))

from enhanced_context_monitor import EnhancedContextMonitor

class ContextMonitorTester:
    """Test suite for Enhanced Context Monitor"""
    
    def __init__(self):
        self.monitor = EnhancedContextMonitor()
        self.test_results = []
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
    
    def test_configuration_loading(self):
        """Test configuration loading and validation"""
        print("\n🧪 Testing Configuration Loading...")
        
        # Test config file exists and loads
        config_exists = self.monitor.config_file.exists()
        self.log_test("Configuration file exists", config_exists)
        
        # Test required config sections exist
        required_sections = ["thresholds", "monitoring", "actions", "display"]
        for section in required_sections:
            has_section = section in self.monitor.config
            self.log_test(f"Config has {section} section", has_section)
        
        # Test threshold values are reasonable
        thresholds = self.monitor.config.get("thresholds", {})
        light = thresholds.get("consolidation_light", 0)
        critical = thresholds.get("consolidation_critical", 0)
        emergency = thresholds.get("sleep_emergency", 0)
        
        logical_order = light < critical < emergency
        self.log_test("Threshold values in logical order", logical_order, 
                     f"Light: {light}%, Critical: {critical}%, Emergency: {emergency}%")
        
        reasonable_values = all(0 <= val <= 100 for val in [light, critical, emergency])
        self.log_test("Threshold values within valid range", reasonable_values)
    
    def test_context_usage_calculation(self):
        """Test context usage calculation and tracking"""
        print("\n🧪 Testing Context Usage Calculation...")
        
        # Test basic usage calculation
        usage_data = self.monitor.get_enhanced_context_usage()
        
        has_required_fields = all(field in usage_data for field in 
                                ["percentage", "timestamp", "threshold_status", "usage_trend"])
        self.log_test("Usage data has required fields", has_required_fields)
        
        # Test usage percentage is valid
        usage_pct = usage_data["percentage"]
        valid_percentage = 0 <= usage_pct <= 100
        self.log_test("Usage percentage in valid range", valid_percentage, f"Usage: {usage_pct}%")
        
        # Test threshold status calculation
        needs_action, threshold_level = self.monitor.check_context_threshold()
        valid_threshold = threshold_level in ["normal", "warning", "critical", "emergency"]
        self.log_test("Threshold status calculation valid", valid_threshold, f"Status: {threshold_level}")
        
        # Test usage history tracking
        time.sleep(1)  # Small delay to ensure different timestamp
        usage_data2 = self.monitor.get_enhanced_context_usage()
        
        history_tracking = len(self.monitor.usage_history) >= 2
        self.log_test("Usage history tracking works", history_tracking, 
                     f"History entries: {len(self.monitor.usage_history)}")
    
    def test_progress_bar_generation(self):
        """Test progress bar visual generation"""
        print("\n🧪 Testing Progress Bar Generation...")
        
        # Test progress bars at different usage levels
        test_cases = [0, 25, 50, 75, 85, 95, 100]
        
        for usage in test_cases:
            progress_bar = self.monitor.get_progress_bar(usage, 20)
            
            # Should contain percentage
            has_percentage = f"{usage}.0%" in progress_bar or f"{usage}%" in progress_bar
            self.log_test(f"Progress bar for {usage}% contains percentage", has_percentage)
            
            # Should have appropriate emoji based on threshold
            if usage >= 95:
                expected_emoji = "🔴"
            elif usage >= 85:
                expected_emoji = "🟠"  
            elif usage >= 75:
                expected_emoji = "🟡"
            else:
                expected_emoji = "🟢"
            
            has_correct_emoji = expected_emoji in progress_bar
            self.log_test(f"Progress bar for {usage}% has correct color", has_correct_emoji, 
                         f"Expected: {expected_emoji}")
    
    def test_threshold_configuration(self):
        """Test threshold configuration management"""
        print("\n🧪 Testing Threshold Configuration...")
        
        # Test updating thresholds
        original_light = self.monitor.warning_threshold
        test_value = 70.0
        
        success = self.monitor.update_threshold("consolidation_light", test_value)
        self.log_test("Threshold update succeeds", success)
        
        updated_correctly = self.monitor.warning_threshold == test_value
        self.log_test("Threshold value updated correctly", updated_correctly, 
                     f"New value: {self.monitor.warning_threshold}%")
        
        # Test invalid threshold names
        invalid_success = self.monitor.update_threshold("invalid_threshold", 50.0)
        self.log_test("Invalid threshold name rejected", not invalid_success)
        
        # Restore original value
        self.monitor.update_threshold("consolidation_light", original_light)
    
    def test_notification_system(self):
        """Test notification and alert system"""
        print("\n🧪 Testing Notification System...")
        
        # Clear any existing warnings
        self.monitor.warnings_sent.clear()
        
        # Test notification generation (this might not trigger based on current usage)
        notifications = self.monitor.check_and_notify_thresholds()
        
        notification_system_works = isinstance(notifications, list)
        self.log_test("Notification system returns valid format", notification_system_works)
        
        # Test notification tracking (prevent duplicates)
        if notifications:
            # Run check again - should not get duplicate notifications
            notifications2 = self.monitor.check_and_notify_thresholds()
            no_duplicates = len(notifications2) == 0
            self.log_test("Duplicate notifications prevented", no_duplicates)
    
    def test_usage_history_analysis(self):
        """Test usage history and trend analysis"""
        print("\n🧪 Testing Usage History Analysis...")
        
        # Generate some history data
        for i in range(5):
            self.monitor.get_enhanced_context_usage()
            time.sleep(0.1)  # Small delay for different timestamps
        
        # Test history summary
        history_summary = self.monitor.get_usage_history_summary(1)  # Last 1 hour
        
        has_required_fields = all(field in history_summary for field in 
                                ["min_usage", "max_usage", "avg_usage", "current_usage", "trend"])
        self.log_test("History summary has required fields", has_required_fields)
        
        # Test data consistency
        if "error" not in history_summary:
            min_usage = history_summary["min_usage"]
            max_usage = history_summary["max_usage"]
            avg_usage = history_summary["avg_usage"]
            
            logical_values = min_usage <= avg_usage <= max_usage
            self.log_test("History values are logically consistent", logical_values,
                         f"Min: {min_usage:.1f}%, Avg: {avg_usage:.1f}%, Max: {max_usage:.1f}%")
    
    def test_display_output(self):
        """Test display output generation"""
        print("\n🧪 Testing Display Output...")
        
        # Test status display
        status_output = self.monitor.display_context_status()
        
        contains_usage = "Current Usage:" in status_output
        self.log_test("Status display contains usage information", contains_usage)
        
        contains_thresholds = "Thresholds:" in status_output
        self.log_test("Status display contains threshold information", contains_thresholds)
        
        contains_progress_bar = "[" in status_output and "]" in status_output
        self.log_test("Status display contains progress bar", contains_progress_bar)
    
    async def test_memory_integration(self):
        """Test integration with memory management system"""
        print("\n🧪 Testing Memory Integration...")
        
        # Test memory consolidation works
        try:
            success = await self.monitor.consolidate_memory("normal")
            self.log_test("Memory consolidation integration works", success)
        except Exception as e:
            self.log_test("Memory consolidation integration works", False, f"Error: {e}")
        
        # Test memory files are created
        memory_dir = Path(".claude/memory")
        essential_file = memory_dir / "ESSENTIAL_WORKFLOW_KNOWLEDGE.md"
        snapshot_file = memory_dir / "LATEST_MEMORY_SNAPSHOT.json"
        
        essential_exists = essential_file.exists()
        snapshot_exists = snapshot_file.exists()
        
        self.log_test("Essential knowledge file exists", essential_exists)
        self.log_test("Memory snapshot file exists", snapshot_exists)
    
    def test_configuration_persistence(self):
        """Test configuration saving and loading"""
        print("\n🧪 Testing Configuration Persistence...")
        
        # Test configuration saving
        original_config = self.monitor.config.copy()
        
        # Modify config
        self.monitor.config["test_key"] = "test_value"
        save_success = self.monitor.save_config()
        self.log_test("Configuration saving works", save_success)
        
        # Test configuration loading
        new_monitor = EnhancedContextMonitor()
        config_loaded = new_monitor.config.get("test_key") == "test_value"
        self.log_test("Configuration loading works", config_loaded)
        
        # Restore original config
        self.monitor.config = original_config
        self.monitor.save_config()
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("🧪 Enhanced Context Monitor Test Suite")
        print("=" * 50)
        
        # Run all tests
        self.test_configuration_loading()
        self.test_context_usage_calculation()
        self.test_progress_bar_generation()
        self.test_threshold_configuration()
        self.test_notification_system()
        self.test_usage_history_analysis()
        self.test_display_output()
        await self.test_memory_integration()
        self.test_configuration_persistence()
        
        # Print summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! Context Monitor is ready for use.")
        else:
            print(f"\n⚠️ {failed_tests} test(s) failed. Review the issues above.")
            
        return failed_tests == 0

async def main():
    """Run the test suite"""
    tester = ContextMonitorTester()
    success = await tester.run_all_tests()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())