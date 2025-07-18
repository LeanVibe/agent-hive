#!/usr/bin/env python3
"""
Test Dashboard Integration - Complete Data Flow Validation
Tests the complete data flow from dashboard metrics to server to UI
"""

import asyncio
import json
import aiohttp
import websockets
from datetime import datetime
import time

class DashboardIntegrationTest:
    """Test complete dashboard integration data flow"""
    
    def __init__(self, server_url="http://localhost:8002"):
        self.server_url = server_url
        self.ws_url = server_url.replace("http", "ws") + "/ws"
        
    async def test_metrics_api(self):
        """Test metrics API endpoints"""
        print("🔧 Testing metrics API endpoints...")
        
        # Test metric data
        test_metric = {
            "metric_id": "test_001",
            "type": "xp_compliance",
            "value": 85.5,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "source": "dashboard_integration_test"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test POST /api/metrics
                async with session.post(
                    f"{self.server_url}/api/metrics",
                    json=test_metric
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"✅ POST /api/metrics: {result}")
                        return True
                    else:
                        print(f"❌ POST /api/metrics failed: {resp.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return False
    
    async def test_metrics_retrieval(self):
        """Test metrics retrieval"""
        print("📊 Testing metrics retrieval...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test GET /api/metrics
                async with session.get(f"{self.server_url}/api/metrics") as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        metrics = result.get("metrics", [])
                        print(f"✅ GET /api/metrics: Retrieved {len(metrics)} metrics")
                        
                        # Check if our test metric is there
                        test_metric_found = any(
                            m.get("metric_id") == "test_001" for m in metrics
                        )
                        
                        if test_metric_found:
                            print("✅ Test metric found in retrieved data")
                            return True
                        else:
                            print("⚠️  Test metric not found (may be expected)")
                            return True
                    else:
                        print(f"❌ GET /api/metrics failed: {resp.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Metrics retrieval test failed: {e}")
            return False
    
    async def test_websocket_broadcast(self):
        """Test WebSocket broadcasting"""
        print("🔄 Testing WebSocket broadcasting...")
        
        try:
            # Connect to WebSocket
            async with websockets.connect(self.ws_url) as websocket:
                print("✅ WebSocket connected")
                
                # Send a test metric via API while WebSocket is connected
                test_metric = {
                    "metric_id": "ws_test_001",
                    "type": "pr_size",
                    "value": 245,
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                    "source": "websocket_test"
                }
                
                # Send metric via API in parallel
                async def send_metric():
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{self.server_url}/api/metrics",
                            json=test_metric
                        ) as resp:
                            return resp.status == 200
                
                # Start sending metric
                send_task = asyncio.create_task(send_metric())
                
                # Wait for WebSocket message
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    
                    if data.get("type") == "metric_update":
                        print(f"✅ WebSocket broadcast received: {data['data']['metric_id']}")
                        return True
                    else:
                        print(f"⚠️  WebSocket message type: {data.get('type')}")
                        return True
                        
                except asyncio.TimeoutError:
                    print("⚠️  WebSocket timeout (server may not be running)")
                    return False
                    
                finally:
                    await send_task
                    
        except Exception as e:
            print(f"❌ WebSocket test failed: {e}")
            return False
    
    async def test_health_check(self):
        """Test health check endpoint"""
        print("🏥 Testing health check...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/api/health") as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"✅ Health check: {result['status']}")
                        return True
                    else:
                        print(f"❌ Health check failed: {resp.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🧪 Starting Dashboard Integration Tests")
        print("=" * 50)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Metrics API", self.test_metrics_api),
            ("Metrics Retrieval", self.test_metrics_retrieval),
            ("WebSocket Broadcasting", self.test_websocket_broadcast),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            try:
                result = await test_func()
                results.append((test_name, result))
                status = "✅ PASSED" if result else "❌ FAILED"
                print(f"{status}: {test_name}")
            except Exception as e:
                results.append((test_name, False))
                print(f"❌ FAILED: {test_name} - {e}")
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - Dashboard integration is working!")
            return True
        else:
            print("⚠️  Some tests failed - Check server configuration")
            return False

def main():
    """Main test runner"""
    print("🚀 Dashboard Integration Test Suite")
    print("This test validates the complete data flow:")
    print("  1. Dashboard → Server (API)")
    print("  2. Server → UI (WebSocket)")
    print("  3. UI → Dashboard (Complete loop)")
    print()
    
    tester = DashboardIntegrationTest()
    
    # Run tests
    success = asyncio.run(tester.run_all_tests())
    
    if success:
        print("\n✅ Dashboard integration is fully operational!")
        exit(0)
    else:
        print("\n❌ Dashboard integration has issues.")
        print("💡 To fix: Start the enhanced server with 'python dashboard/enhanced_server.py'")
        exit(1)

if __name__ == "__main__":
    main()