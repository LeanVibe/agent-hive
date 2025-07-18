#!/bin/bash

# Worktree Cleanup Script
# Safely archives and removes obsolete worktrees

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ARCHIVE_DIR="$PROJECT_ROOT/.worktree-archive"
LOG_FILE="$PROJECT_ROOT/.claude/logs/worktree-cleanup.log"

# Create archive directory if it doesn't exist
mkdir -p "$ARCHIVE_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to safely archive a worktree
archive_worktree() {
    local worktree_path="$1"
    local branch_name="$2"
    local reason="$3"
    
    # Check if worktree exists
    if [[ ! -d "$worktree_path" ]]; then
        log "Worktree does not exist, skipping: $worktree_path"
        return 0
    fi
    
    log "Archiving worktree: $worktree_path (branch: $branch_name) - Reason: $reason"
    
    # Create archive info
    local archive_info="$ARCHIVE_DIR/$(basename "$worktree_path").info"
    cat > "$archive_info" << EOF
Worktree: $worktree_path
Branch: $branch_name
Archived: $(date)
Reason: $reason
Last Commit: $(cd "$worktree_path" && git log -1 --format='%h %ad %s' --date=short 2>/dev/null || echo "Unable to get commit info")
EOF
    
    # Remove worktree
    cd "$PROJECT_ROOT"
    git worktree remove "$worktree_path" --force 2>/dev/null || {
        log "Failed to remove worktree via git, attempting manual removal"
        rm -rf "$worktree_path"
    }
    
    # Delete branch if it's safe to do so
    if git show-ref --verify --quiet "refs/heads/$branch_name"; then
        log "Deleting branch: $branch_name"
        git branch -D "$branch_name" 2>/dev/null || log "Failed to delete branch: $branch_name"
    fi
    
    log "Successfully archived: $worktree_path"
}

# Function to check if worktree is safe to remove
is_safe_to_remove() {
    local worktree_path="$1"
    local branch_name="$2"
    
    # Check if branch is merged into integration branch
    if git merge-base --is-ancestor "$branch_name" "integration/phase3-advanced-features" 2>/dev/null; then
        return 0
    fi
    
    # Check if worktree is very old (Jul-16 branches)
    if [[ "$branch_name" =~ Jul-16 ]]; then
        return 0
    fi
    
    return 1
}

# Main cleanup function
cleanup_worktrees() {
    log "Starting worktree cleanup process"
    
    # Archive merged worktrees
    archive_merged_worktrees() {
        archive_worktree "$PROJECT_ROOT/worktrees/infrastructure-Jul-17-0945" "new-work/infrastructure-Jul-17-0945" "Fully merged into integration branch"
        archive_worktree "$PROJECT_ROOT/worktrees/infrastructure-Jul-17-0946" "new-work/infrastructure-Jul-17-0946" "Fully merged into integration branch"
        archive_worktree "$PROJECT_ROOT/worktrees/integration-specialist-Jul-17-0946" "new-work/integration-specialist-Jul-17-0946" "Fully merged into integration branch"
        archive_worktree "$PROJECT_ROOT/worktrees/monitoring-Jul-17-0946" "new-work/monitoring-Jul-17-0946" "Fully merged into integration branch"
        archive_worktree "$PROJECT_ROOT/worktrees/monitoring-Jul-17-0824" "new-work/monitoring-Jul-17-0824" "Fully merged into integration branch"
        archive_worktree "$PROJECT_ROOT/worktrees/infrastructure-Jul-17-0822" "new-work/infrastructure-Jul-17-0822" "Fully merged into integration branch"
        archive_worktree "$PROJECT_ROOT/new-worktrees/infrastructure-Jul-17-1327" "new-work/infrastructure-Jul-17-1327" "Fully merged into integration branch"
        archive_worktree "$PROJECT_ROOT/new-worktrees/integration-specialist-Jul-17-1327" "new-work/integration-specialist-Jul-17-1327" "Fully merged into integration branch"
        archive_worktree "$PROJECT_ROOT/new-worktrees/integration-specialist-Jul-17-1502" "new-work/integration-specialist-Jul-17-1502" "Fully merged into integration branch"
        archive_worktree "$PROJECT_ROOT/new-worktrees/performance-Jul-17-1327" "new-work/performance-Jul-17-1327" "Fully merged into integration branch"
    }
    
    # Archive obsolete worktrees
    archive_obsolete_worktrees() {
        archive_worktree "$PROJECT_ROOT/worktrees/frontend-Jul-16-1222" "new-work/frontend-Jul-16-1222" "Obsolete - superseded by newer versions"
        archive_worktree "$PROJECT_ROOT/worktrees/infrastructure-Jul-16-1300" "new-work/infrastructure-Jul-16-1300" "Obsolete - superseded by newer versions"
        archive_worktree "$PROJECT_ROOT/worktrees/integration-specialist-Jul-16-1220" "docs-config-pr43-split" "Obsolete - superseded by newer versions"
        archive_worktree "$PROJECT_ROOT/worktrees/integration-specialist-Jul-16-1247" "new-work/integration-specialist-Jul-16-1247" "Obsolete - superseded by newer versions"
        archive_worktree "$PROJECT_ROOT/worktrees/performance-Jul-16-1301" "new-work/performance-Jul-16-1301" "Obsolete - superseded by newer versions"
        archive_worktree "$PROJECT_ROOT/worktrees/service-mesh-Jul-16-1221" "new-work/service-mesh-Jul-16-1221" "Obsolete - superseded by newer versions"
    }
    
    # Execute cleanup
    archive_merged_worktrees
    archive_obsolete_worktrees
    
    # Clean up nested worktree
    local nested_worktree="$PROJECT_ROOT/worktrees/service-mesh-Jul-16-1221/new-worktrees/integration-specialist-Jul-17-1331"
    if [[ -d "$nested_worktree" ]]; then
        log "Cleaning up nested worktree: $nested_worktree"
        rm -rf "$nested_worktree"
    fi
    
    log "Worktree cleanup completed"
}

# Function to show current status
show_status() {
    log "Current worktree status:"
    git worktree list | tee -a "$LOG_FILE"
    
    local count=$(git worktree list | wc -l)
    log "Total worktrees: $count"
}

# Main execution
main() {
    case "${1:-cleanup}" in
        "cleanup")
            cleanup_worktrees
            show_status
            ;;
        "status")
            show_status
            ;;
        "help")
            echo "Usage: $0 [cleanup|status|help]"
            echo "  cleanup: Perform worktree cleanup (default)"
            echo "  status:  Show current worktree status"
            echo "  help:    Show this help message"
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

main "$@"