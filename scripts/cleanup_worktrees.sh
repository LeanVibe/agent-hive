#!/bin/bash
#
# scripts/cleanup_worktrees.sh
#
# This script automates the cleanup of Git worktrees.
# It identifies and removes worktrees linked to merged or deleted branches.

set -e

# --- Helper Functions ---

# Function to print colored output
print_info() {
    echo -e "\033[34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[32m[SUCCESS]\033[0m $1"
}

print_warning() {
    echo -e "\033[33m[WARNING]\033[0m $1"
}

print_error() {
    echo -e "\033[31m[ERROR]\033[0m $1" >&2
}

# --- Main Logic ---

# Get the main branch name (main or master)
main_branch=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')

print_info "Main branch identified as: $main_branch"
print_info "Fetching latest remote state..."
git fetch --prune

# Get a list of all local branches that have been merged into the main branch
merged_branches=$(git branch --merged "$main_branch" | grep -v '^[ *]*master$' | grep -v '^[ *]*main$' | sed 's/^[ *]*//')

# Get a list of remote branches to check against
remote_branches=$(git branch -r | sed 's@ *origin/@@')

# Get a list of current worktree paths and their branches
worktrees=$(git worktree list | awk '{print $1, $2}')

if [ -z "$worktrees" ]; then
    print_success "No worktrees found to clean up."
    exit 0
fi

print_info "Scanning worktrees for cleanup..."
echo "-------------------------------------"

while IFS= read -r line; do
    path=$(echo "$line" | awk '{print $1}')
    branch=$(echo "$line" | awk '{print $2}')
    
    # Skip the main worktree (project root)
    if [ "$path" == "$(git rev-parse --show-toplevel)" ]; then
        continue
    fi
    
    is_merged=false
    # Check if the worktree's branch has been merged
    if echo "$merged_branches" | grep -q "^$branch$"; then
        is_merged=true
    fi

    branch_exists=false
    # Check if the branch still exists locally or remotely
    if git rev-parse --verify "$branch" >/dev/null 2>&1 || echo "$remote_branches" | grep -q "^$branch$"; then
        branch_exists=true
    fi

    if [ "$is_merged" == "true" ] || [ "$branch_exists" == "false" ]; then
        print_warning "Worktree at '$path' is on branch '$branch' which is merged or deleted."
        
        # In a real-world scenario, you might prompt here.
        # For automation, we will proceed with cleanup.
        print_info "Removing worktree for branch '$branch'..."
        git worktree remove "$path" --force
        
        print_info "Deleting local branch '$branch'..."
        git branch -d "$branch" || true # Use true to avoid error if branch is already gone
        
        print_success "Cleanup for '$path' complete."
    else
        print_info "Worktree at '$path' for branch '$branch' is active and safe."
    fi
    echo "-------------------------------------"
done <<< "$worktrees"

print_success "Worktree cleanup scan complete." 