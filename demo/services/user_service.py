
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
