# Production Message Bus Architecture

## 🎯 **Mission: Replace tmux with Enterprise Message Bus**

### **Current State Problems**
- ❌ tmux sessions fragile and unreliable
- ❌ No message persistence or retry logic  
- ❌ Manual window management 
- ❌ No scalability or fault tolerance
- ❌ Terminal injection security risks

### **Target Architecture: Redis + AsyncIO Message Bus**

```
┌─────────────────────────────────────────────────────────────┐
│                    Message Bus Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Agent A  ──┐                                               │
│             │    ┌─────────────────┐     ┌─────────────────┐│
│  Agent B  ──┼───▶│  Message Router │────▶│   Redis Broker  ││
│             │    │    (AsyncIO)    │     │   (Pub/Sub +    ││
│  Agent C  ──┘    │                 │     │    Streams)     ││
│                  └─────────────────┘     └─────────────────┘│
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │ Message Queue   │    │ Delivery Status │                 │
│  │ (Persistence)   │    │   (Tracking)    │                 │
│  └─────────────────┘    └─────────────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Core Components**

#### 1. **Redis Message Broker**
- **Pub/Sub Channels**: Real-time message delivery
- **Streams**: Message persistence and replay
- **Sorted Sets**: Priority queues and scheduling
- **Hash Maps**: Agent metadata and routing tables

#### 2. **Message Protocol** 
```json
{
  "message_id": "uuid4",
  "from_agent": "pm-agent", 
  "to_agent": "frontend-agent",
  "message_type": "task_assignment",
  "priority": "high",
  "timestamp": "2025-07-16T12:35:00Z",
  "ttl": 3600,
  "body": {
    "content": "Implement message bus",
    "context": {...},
    "metadata": {...}
  },
  "delivery_options": {
    "require_ack": true,
    "max_retries": 3,
    "retry_delay": 30
  }
}
```

#### 3. **Agent Communication Interface**
- **Async Publisher**: Send messages to other agents  
- **Async Subscriber**: Receive and process messages
- **Message Acknowledgment**: Delivery confirmation
- **Dead Letter Queue**: Failed message handling

#### 4. **Routing Engine**
- **Topic-based routing**: agent.{name}.{message_type}
- **Load balancing**: Round-robin for agent pools
- **Failover**: Automatic rerouting on agent failure
- **Broadcast**: Send to multiple agents

### **Benefits Over tmux**

| Feature | tmux | Redis Message Bus |
|---------|------|-------------------|
| Reliability | ❌ Session crashes | ✅ Persistent queues |
| Scalability | ❌ Manual sessions | ✅ Horizontal scaling |
| Monitoring | ❌ No visibility | ✅ Metrics + dashboards |
| Security | ❌ Terminal injection | ✅ Authenticated channels |
| Message History | ❌ Lost on restart | ✅ Persistent streams |
| Error Handling | ❌ Silent failures | ✅ Retry + DLQ |

### **Implementation Priority**

1. **Phase 1**: Core Redis pub/sub replacement for agent_communicate.py
2. **Phase 2**: Message persistence and delivery guarantees  
3. **Phase 3**: Advanced routing and load balancing
4. **Phase 4**: Monitoring, metrics, and observability

### **Migration Strategy**

1. **Parallel deployment**: Run both systems temporarily
2. **Gradual migration**: Move agents one by one  
3. **Validation**: Compare message delivery success rates
4. **Cutover**: Disable tmux when 100% validated