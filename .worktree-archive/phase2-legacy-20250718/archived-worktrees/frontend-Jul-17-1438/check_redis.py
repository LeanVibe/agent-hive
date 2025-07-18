
import redis
import json

try:
    r = redis.Redis(host="localhost", port=6379, db=0)
    r.ping()
    print(json.dumps({"redis_status": "connected", "info": str(r.info())[0:200]}))
except Exception as e:
    print(json.dumps({"redis_status": "error", "error": str(e)}))
