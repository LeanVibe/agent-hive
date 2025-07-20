
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
