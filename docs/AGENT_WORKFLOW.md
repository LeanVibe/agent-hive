# Simple Agent Workflow

## 🎯 **Core Principle: Keep It Simple**

### **3 Simple Rules**
1. **Work from `agent-integration` branch** (not main)
2. **Keep changes small** (<50 lines per PR)
3. **One agent at a time** (sequential merging)

---

## **📋 Agent Workflow Steps**

### **1. Start New Agent Work**
```bash
# Switch to agent-integration branch
git checkout agent-integration
git pull origin agent-integration

# Create your agent work branch
git checkout -b agent-work/your-agent-name-task
```

### **2. Do Your Agent Work**
- **Keep changes focused and small** (<50 lines)
- **Test your changes** before committing
- **Follow existing code patterns**

### **3. Create Pull Request**
```bash
# Commit your changes
git add .
git commit -m "agent: your description

✅ Tests pass
✅ Changes <50 lines  
✅ Documentation updated (if needed)

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push and create PR to agent-integration (not main!)
git push -u origin agent-work/your-agent-name-task
gh pr create --base agent-integration --title "Agent: Your Task" --body "Brief description"
```

### **4. Integration Process**
- **Sequential merging**: Only 1 agent PR merged at a time
- **Quick review**: Focus on integration, not perfection
- **Merge immediately**: If tests pass and no conflicts

---

## **✅ Success Criteria Template**

Before starting any agent work, define 3 simple success criteria:

```
## Agent Success Criteria
- ✅ **Functional**: [What should work]
- ✅ **Quality**: [Tests pass, no warnings]  
- ✅ **Integration**: [No conflicts, <50 lines]
```

---

## **🚦 Simple Quality Gates**

### **Before Creating PR**
- [ ] Changes are <50 lines
- [ ] Tests pass locally
- [ ] No merge conflicts with agent-integration
- [ ] Clear description of what was done

### **Before Merging**
- [ ] PR targets `agent-integration` (not main)
- [ ] CI passes
- [ ] No conflicts
- [ ] Quick review completed

---

## **📊 Success Metrics**

### **What We Track**
- **Integration success rate**: Target >95%
- **Time to merge**: Target <30 minutes
- **Merge conflicts**: Target 0 per week

### **What We Don't Track (Keep It Simple)**
- Complex velocity metrics
- Detailed time tracking
- Elaborate quality scores

---

## **🛠️ Tools & Commands**

### **Daily Sync (Automated)**
```bash
# Run automatically daily at 9am
./scripts/daily_sync.sh
```

### **Check Your Change Size**
```bash
# See how many lines you've changed
git diff --stat
```

### **Quick Integration Test**
```bash
# Test merge with agent-integration before PR
git checkout agent-integration
git pull origin agent-integration
git merge your-branch --no-commit --no-ff
git merge --abort  # If test successful
```

---

## **🎯 When to Ask for Help**

### **Immediate Help Needed**
- Merge conflicts you can't resolve
- Changes growing beyond 50 lines
- Tests failing for unknown reasons

### **How to Get Help**
1. **Document the issue** clearly
2. **Show what you tried** 
3. **Ask specific questions**

---

*Simple Agent Workflow*  
*Maximum Value, Minimum Complexity*  
*One Agent at a Time, Small Changes, Quick Integration*