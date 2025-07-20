
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
