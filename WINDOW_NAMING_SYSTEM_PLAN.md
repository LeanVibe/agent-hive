# 🔧 Agent-Hive Window Naming System - Real-time Status Plan

**Generated**: July 18, 2025 2:00 PM  
**Status**: 🎯 **FOCUSED PLAN** - Fix window naming with real-time status emoticons  
**Problem**: Agent-hive windows show static names without agent focus and status updates

## 📊 **CURRENT STATE ANALYSIS**

### **Current Window Names (Static)**
```bash
tmux list-windows -t agent-hive -F "#{window_name}"
```
- `SEC-Input-⏳` (Security agent)
- `PERF-Input-⏳` (Performance agent)
- `FE-Input-⏳` (Frontend agent)
- `PM-Input-⏳` (PM agent)

### **Issues Identified**
1. **Static Names**: Windows never update from initial `*-Input-⏳` format
2. **No Status Tracking**: No indication of agent activity or focus
3. **No Real-time Updates**: Names don't reflect current agent state
4. **Missing Background Process**: No continuous monitoring system

### **Desired Window Names (Dynamic)**
```bash
# Real-time status examples
SEC-SecurityAudit-🔄    # Security agent working on audit
PERF-TechDebt-⚠️        # Performance agent addressing technical debt  
FE-Dashboard-✅         # Frontend agent completed dashboard work
PM-Coordination-💭      # PM agent thinking/planning
```

## 🎯 **SOLUTION ARCHITECTURE**

### **Core Components**
1. **Window Status Detector**: Analyze tmux pane content to determine agent activity
2. **Status Classifier**: Map agent activity to meaningful status categories
3. **Window Name Generator**: Create descriptive names with appropriate emoticons
4. **Background Updater**: Continuous monitoring and updating process
5. **Configuration Manager**: Customizable status patterns and emoticons

### **Status Detection Strategy**
```python
# Agent activity detection patterns
activity_patterns = {
    'processing': ['Processing', 'Analyzing', 'Generating', 'Working on'],
    'thinking': ['Thinking', 'Planning', 'Considering', 'Evaluating'],
    'waiting': ['-- INSERT --', '>', 'waiting for', 'What should I'],
    'error': ['Error', 'Failed', 'Exception', 'traceback'],
    'complete': ['Complete', 'Done', 'Finished', 'SUCCESS'],
    'idle': ['claude@', '$', 'tmux', 'zsh']
}
```

### **Emoticon Mapping**
```python
status_emoticons = {
    'processing': '🔄',  # Working/in progress
    'thinking': '💭',    # Thinking/planning
    'waiting': '⏳',     # Waiting for input
    'error': '❌',       # Error/failed
    'complete': '✅',    # Successfully completed
    'idle': '⏸️',       # Idle/ready
    'focused': '🎯',     # Focused on specific task
    'reviewing': '👀',   # Reviewing/analyzing
    'testing': '🧪',     # Testing/validation
    'crisis': '🚨'       # Crisis/urgent
}
```

## 🚀 **IMPLEMENTATION PLAN**

### **Phase 1: Core Window Updater (45 minutes)**
**Create `scripts/tmux_window_updater.py`**

#### **Key Features**
1. **Real-time Detection**: Monitor tmux pane content every 30 seconds
2. **Intelligent Parsing**: Extract agent activity from pane content
3. **Status Classification**: Map activity to meaningful categories
4. **Dynamic Naming**: Generate descriptive window names
5. **Background Process**: Run continuously without interruption

#### **Implementation Structure**
```python
class AgentWindowUpdater:
    def __init__(self):
        self.session_name = "agent-hive"
        self.window_mapping = self._discover_agent_windows()
        self.activity_patterns = self._load_activity_patterns()
        self.status_emoticons = self._load_status_emoticons()
        
    def detect_agent_activity(self, window_name):
        """Analyze pane content to determine agent activity"""
        
    def classify_status(self, content):
        """Classify agent status based on content analysis"""
        
    def generate_window_name(self, agent_name, activity, status):
        """Generate descriptive window name with emoticon"""
        
    def update_window_name(self, old_name, new_name):
        """Update tmux window name"""
        
    def monitor_continuously(self, interval=30):
        """Run continuous monitoring and updates"""
```

### **Phase 2: Enhanced Status Detection (30 minutes)**
**Advanced activity recognition and context awareness**

#### **Context-Aware Detection**
```python
def detect_agent_context(self, pane_content):
    """Detect what the agent is working on"""
    
    context_patterns = {
        'security_audit': ['security', 'vulnerability', 'audit', 'bandit'],
        'performance_opt': ['performance', 'optimization', 'mypy', 'technical debt'],
        'frontend_dev': ['frontend', 'dashboard', 'UI', 'component'],
        'coordination': ['coordination', 'sprint', 'planning', 'agents'],
        'crisis_response': ['crisis', 'emergency', 'critical', 'urgent']
    }
    
    # Return detected context and confidence level
    return context, confidence
```

#### **Smart Status Transitions**
```python
def track_status_transitions(self, agent_name, old_status, new_status):
    """Track and log status transitions for insights"""
    
    transition_log = {
        'timestamp': datetime.now(),
        'agent': agent_name,
        'from_status': old_status,
        'to_status': new_status,
        'duration': self.calculate_duration(agent_name, old_status)
    }
    
    self.log_transition(transition_log)
```

### **Phase 3: Background Process Integration (30 minutes)**
**Ensure continuous operation and system integration**

#### **Daemon Process Setup**
```python
def start_background_monitoring(self):
    """Start background monitoring process"""
    
    # Create daemon process
    # Handle graceful shutdown
    # Log monitoring activity
    # Error recovery and restart
```

#### **System Integration**
```bash
# Start monitoring automatically
python scripts/tmux_window_updater.py --daemon

# Check monitoring status
python scripts/tmux_window_updater.py --status

# Stop monitoring
python scripts/tmux_window_updater.py --stop
```

### **Phase 4: Configuration and Customization (15 minutes)**
**Allow customization of patterns and emoticons**

#### **Configuration File: `config/window_updater.yaml`**
```yaml
# Window naming configuration
update_interval: 30  # seconds
session_name: "agent-hive"

# Status patterns
activity_patterns:
  processing: ["Processing", "Analyzing", "Generating"]
  thinking: ["Thinking", "Planning", "Considering"]
  waiting: ["-- INSERT --", ">", "waiting for"]
  error: ["Error", "Failed", "Exception"]
  complete: ["Complete", "Done", "Finished"]

# Emoticon mapping
status_emoticons:
  processing: "🔄"
  thinking: "💭"
  waiting: "⏳"
  error: "❌"
  complete: "✅"
  idle: "⏸️"

# Agent-specific overrides
agent_overrides:
  security:
    patterns:
      audit: ["security", "vulnerability", "audit"]
    emoticons:
      audit: "🔍"
```

## 🧪 **TESTING STRATEGY**

### **Unit Tests**
```python
# Test activity detection
def test_activity_detection():
    updater = AgentWindowUpdater()
    content = "Processing security audit results..."
    status = updater.classify_status(content)
    assert status == 'processing'

# Test window name generation
def test_window_name_generation():
    updater = AgentWindowUpdater()
    name = updater.generate_window_name("security", "audit", "processing")
    assert name == "SEC-Audit-🔄"
```

### **Integration Tests**
```python
# Test tmux integration
def test_tmux_window_update():
    updater = AgentWindowUpdater()
    success = updater.update_window_name("SEC-Input-⏳", "SEC-Audit-🔄")
    assert success == True

# Test background process
def test_background_monitoring():
    updater = AgentWindowUpdater()
    updater.start_background_monitoring()
    # Verify process is running
    # Verify window names are updating
```

### **System Tests**
```bash
# Test real-time updates
python scripts/tmux_window_updater.py --test

# Test integration with agents
python scripts/fixed_agent_communication.py --agent security --message "Start security audit"
# Verify window name changes to SEC-Audit-🔄
```

## 📋 **DETAILED IMPLEMENTATION SCHEDULE**

### **Hour 1: Core Implementation (60 minutes)**
1. **Create base class structure** (15 min)
2. **Implement activity detection** (20 min)
3. **Add status classification** (15 min)
4. **Create window name generator** (10 min)

### **Hour 2: Integration and Testing (60 minutes)**
1. **Add tmux integration** (20 min)
2. **Create background monitoring** (20 min)
3. **Write unit tests** (20 min)

### **Hour 3: Polish and Documentation (60 minutes)**
1. **Add configuration system** (20 min)
2. **Create system integration** (20 min)
3. **Write documentation** (20 min)

## 🎯 **SUCCESS CRITERIA**

### **Immediate Success (Hour 1)**
- [ ] Window names update in real-time
- [ ] Status emoticons reflect agent activity
- [ ] Agent focus is clearly visible
- [ ] No manual intervention required

### **System Success (Hour 2)**
- [ ] Background monitoring runs continuously
- [ ] Status transitions are smooth and accurate
- [ ] Error handling prevents crashes
- [ ] Performance impact is minimal

### **Long-term Success (Hour 3)**
- [ ] Customizable patterns and emoticons
- [ ] System integration with agent communication
- [ ] Comprehensive logging and monitoring
- [ ] Documentation and maintenance procedures

## 🔍 **GEMINI CLI EVALUATION QUESTIONS**

### **Technical Architecture**
1. **Is the activity detection approach robust and reliable?**
2. **Are the status classifications comprehensive and meaningful?**
3. **Is the background monitoring architecture sound?**

### **Implementation Strategy**
1. **Is the 3-hour implementation timeline realistic?**
2. **Are there potential performance or resource concerns?**
3. **What edge cases or failure modes should be considered?**

### **System Integration**
1. **How well does this integrate with existing agent communication?**
2. **Are there potential conflicts with tmux or other systems?**
3. **What maintenance or monitoring requirements exist?**

### **User Experience**
1. **Do the proposed window names provide clear, actionable information?**
2. **Are the emoticons intuitive and helpful?**
3. **Is the system sufficiently customizable for different use cases?**

---

**Status**: 🎯 **COMPREHENSIVE PLAN READY** - Real-time window naming with status emoticons  
**Timeline**: **3 hours** for complete implementation  
**Priority**: **High** - Essential for agent monitoring and coordination  
**Next Action**: Evaluate plan with Gemini CLI, then implement core updater