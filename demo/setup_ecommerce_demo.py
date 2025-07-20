#!/usr/bin/env python3
"""
Setup script for Agent Hive E-Commerce Deployment Demo.

This script initializes the demo environment for the Zero-Downtime 
Multi-Service Deployment demonstration.
"""

import os
import sys
import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, List

def print_status(message: str, status: str = "INFO"):
    """Print formatted status message."""
    timestamp = time.strftime("%H:%M:%S")
    status_color = {
        "INFO": "\033[94m",  # Blue
        "SUCCESS": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m"   # Red
    }
    reset_color = "\033[0m"
    
    print(f"{status_color.get(status, '')}{timestamp} [{status}] {message}{reset_color}")

def setup_demo_database():
    """Create demo database with service configurations."""
    print_status("Setting up demo database...")
    
    demo_dir = Path(__file__).parent
    db_path = demo_dir / "ecommerce_demo.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create services table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            port INTEGER NOT NULL,
            status TEXT DEFAULT 'stopped',
            health_endpoint TEXT,
            dependencies TEXT,
            deployment_time INTEGER DEFAULT 0,
            last_deployed TIMESTAMP
        )
    """)
    
    # Insert demo services
    services = [
        ("api-gateway", 8000, "/health", "[]", 10),
        ("user-service", 8001, "/health", '["api-gateway"]', 15),
        ("product-service", 8002, "/health", '["api-gateway"]', 12),
        ("order-service", 8003, "/health", '["user-service", "product-service"]', 18),
        ("payment-service", 8004, "/health", '["order-service"]', 14)
    ]
    
    for name, port, health_endpoint, dependencies, deployment_time in services:
        cursor.execute("""
            INSERT OR REPLACE INTO services 
            (name, port, health_endpoint, dependencies, deployment_time)
            VALUES (?, ?, ?, ?, ?)
        """, (name, port, health_endpoint, dependencies, deployment_time))
    
    # Create deployment logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deployment_logs (
            id INTEGER PRIMARY KEY,
            service_name TEXT,
            action TEXT,
            status TEXT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    
    print_status("Demo database initialized", "SUCCESS")
    return str(db_path)

def create_mock_services():
    """Create mock service files for demonstration."""
    print_status("Creating mock service implementations...")
    
    demo_dir = Path(__file__).parent
    services_dir = demo_dir / "services"
    services_dir.mkdir(exist_ok=True)
    
    services = {
        "api_gateway.py": """
import time
import random

class APIGateway:
    def __init__(self):
        self.status = "stopped"
        self.health_score = 100
    
    def start(self):
        print("🚀 Starting API Gateway...")
        time.sleep(1)
        self.status = "running"
        print("✅ API Gateway started successfully")
    
    def health_check(self):
        # Simulate occasional health fluctuations
        self.health_score = random.randint(85, 100)
        return {
            "status": self.status,
            "health": self.health_score,
            "uptime": time.time()
        }
    
    def stop(self):
        self.status = "stopped"
        print("🛑 API Gateway stopped")
""",
        
        "user_service.py": """
import time
import random

class UserService:
    def __init__(self):
        self.status = "stopped"
        self.connections = 0
    
    def start(self):
        print("👤 Starting User Service...")
        time.sleep(1.5)
        self.status = "running"
        self.connections = random.randint(10, 50)
        print(f"✅ User Service started - {self.connections} active connections")
    
    def health_check(self):
        return {
            "status": self.status,
            "active_users": self.connections,
            "auth_latency": random.randint(50, 200)
        }
    
    def stop(self):
        self.status = "stopped"
        print("🛑 User Service stopped")
""",
        
        "product_service.py": """
import time
import random

class ProductService:
    def __init__(self):
        self.status = "stopped"
        self.cache_hit_rate = 0
    
    def start(self):
        print("📦 Starting Product Service...")
        time.sleep(1.2)
        self.status = "running"
        self.cache_hit_rate = random.randint(75, 95)
        print(f"✅ Product Service started - {self.cache_hit_rate}% cache hit rate")
    
    def health_check(self):
        return {
            "status": self.status,
            "cache_hit_rate": self.cache_hit_rate,
            "inventory_items": random.randint(1000, 5000)
        }
    
    def stop(self):
        self.status = "stopped"
        print("🛑 Product Service stopped")
""",
        
        "order_service.py": """
import time
import random

class OrderService:
    def __init__(self):
        self.status = "stopped"
        self.pending_orders = 0
    
    def start(self):
        print("🛒 Starting Order Service...")
        time.sleep(1.8)
        self.status = "running"
        self.pending_orders = random.randint(5, 25)
        print(f"✅ Order Service started - {self.pending_orders} pending orders")
    
    def health_check(self):
        return {
            "status": self.status,
            "pending_orders": self.pending_orders,
            "processing_time": random.randint(500, 2000)
        }
    
    def stop(self):
        self.status = "stopped"
        print("🛑 Order Service stopped")
""",
        
        "payment_service.py": """
import time
import random

class PaymentService:
    def __init__(self):
        self.status = "stopped"
        self.transaction_rate = 0
    
    def start(self):
        print("💳 Starting Payment Service...")
        time.sleep(1.4)
        self.status = "running"
        self.transaction_rate = random.randint(80, 98)
        print(f"✅ Payment Service started - {self.transaction_rate}% success rate")
    
    def health_check(self):
        return {
            "status": self.status,
            "success_rate": self.transaction_rate,
            "daily_volume": random.randint(1000, 10000)
        }
    
    def stop(self):
        self.status = "stopped"
        print("🛑 Payment Service stopped")
"""
    }
    
    for filename, content in services.items():
        service_file = services_dir / filename
        with open(service_file, 'w') as f:
            f.write(content)
    
    # Create __init__.py
    init_file = services_dir / "__init__.py"
    with open(init_file, 'w') as f:
        f.write("# E-Commerce Demo Services\n")
    
    print_status(f"Created {len(services)} mock services", "SUCCESS")

def create_demo_config():
    """Create demo configuration file."""
    print_status("Creating demo configuration...")
    
    demo_dir = Path(__file__).parent
    config = {
        "demo_environment": {
            "name": "E-Commerce Platform Demo",
            "version": "1.0.0",
            "services": [
                {
                    "name": "api-gateway",
                    "description": "Main traffic router",
                    "critical": True,
                    "startup_time": 10
                },
                {
                    "name": "user-service", 
                    "description": "User authentication and management",
                    "critical": True,
                    "startup_time": 15
                },
                {
                    "name": "product-service",
                    "description": "Product inventory and catalog",
                    "critical": True,
                    "startup_time": 12
                },
                {
                    "name": "order-service",
                    "description": "Order processing and management",
                    "critical": True,
                    "startup_time": 18
                },
                {
                    "name": "payment-service",
                    "description": "Payment processing",
                    "critical": True,
                    "startup_time": 14
                }
            ]
        },
        "deployment_simulation": {
            "manual_process_time": 240,  # 4 minutes (scaled down from 4 hours)
            "agent_hive_time": 75,       # 75 seconds (scaled down from 15 minutes)
            "failure_rate_manual": 20,   # 20% failure rate for manual
            "failure_rate_agent": 5      # 5% failure rate for Agent Hive
        }
    }
    
    config_file = demo_dir / "demo_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print_status("Demo configuration created", "SUCCESS")
    return str(config_file)

def verify_agent_hive_components():
    """Verify that Agent Hive components are available."""
    print_status("Verifying Agent Hive components...")
    
    try:
        # Try to import core components
        sys.path.append(str(Path(__file__).parent.parent))
        
        from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
        print_status("✅ Multi-Agent Coordinator available", "SUCCESS")
        
        from external_api.service_discovery import ServiceDiscovery
        print_status("✅ Service Discovery available", "SUCCESS")
        
        print_status("All required components verified", "SUCCESS")
        return True
        
    except ImportError as e:
        print_status(f"Component verification failed: {e}", "ERROR")
        print_status("Demo will run in simulation mode", "WARNING")
        return False

def main():
    """Main setup function."""
    print_status("🚀 Initializing Agent Hive E-Commerce Demo Environment", "INFO")
    print_status("=" * 60, "INFO")
    
    # Setup components
    db_path = setup_demo_database()
    create_mock_services()
    config_path = create_demo_config()
    components_available = verify_agent_hive_components()
    
    print_status("=" * 60, "INFO")
    print_status("🎉 Demo Environment Setup Complete!", "SUCCESS")
    print_status("", "INFO")
    print_status("📁 Demo Structure:", "INFO")
    print_status(f"  📄 Database: {db_path}", "INFO")
    print_status(f"  📄 Config: {config_path}", "INFO")
    print_status(f"  📁 Services: demo/services/", "INFO")
    print_status("", "INFO")
    
    if components_available:
        print_status("✅ Ready for live Agent Hive demonstration", "SUCCESS")
    else:
        print_status("⚠️  Running in simulation mode", "WARNING")
    
    print_status("", "INFO")
    print_status("🎬 Next Steps:", "INFO")
    print_status("  1. Run manual deployment simulation:", "INFO")
    print_status("     python demo/manual_deployment_simulation.py", "INFO")
    print_status("  2. Run Agent Hive autonomous deployment:", "INFO")
    print_status("     python demo/ecommerce_deployment.py", "INFO")
    print_status("  3. Test failure recovery:", "INFO")
    print_status("     python demo/simulate_deployment_failure.py", "INFO")

if __name__ == "__main__":
    main()