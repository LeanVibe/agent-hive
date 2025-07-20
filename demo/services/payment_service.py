
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
