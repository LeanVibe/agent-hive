
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
