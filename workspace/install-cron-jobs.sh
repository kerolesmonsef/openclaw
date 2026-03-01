#!/bin/bash

# Install Stock Analysis Cron Jobs
# Sets up daily and weekly cron jobs for stock analysis

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="/home/kero/.openclaw/workspace"
LOG_DIR="$SCRIPT_DIR/logs"

# Function to print colored output
print_status() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${NC}"
}

# Function to check if cron job exists
cron_job_exists() {
    local schedule="$1"
    local command="$2"
    crontab -l 2>/dev/null | grep -q "$schedule.*$command"
}

# Function to add cron job
add_cron_job() {
    local schedule="$1"
    local command="$2"
    local description="$3"
    
    if cron_job_exists "$schedule" "$command"; then
        print_status "$YELLOW" "- $description: Already exists"
    else
        (crontab -l 2>/dev/null; echo "$schedule $command") | crontab -
        if cron_job_exists "$schedule" "$command"; then
            print_status "$GREEN" "- $description: Added successfully"
        else
            print_status "$RED" "- $description: Failed to add"
        fi
    fi
}

# Function to create log directory
create_log_directory() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        if [ -d "$LOG_DIR" ]; then
            print_status "$GREEN" "- Log directory created: $LOG_DIR"
        else
            print_status "$RED" "- Failed to create log directory"
        fi
    else
        print_status "$YELLOW" "- Log directory already exists: $LOG_DIR"
    fi
}

# Function to test scripts
test_scripts() {
    print_status "$YELLOW" "Testing scripts..."
    
    # Test stock analysis controller
    if [ -x "$SCRIPT_DIR/stock-analysis-controller.sh" ]; then
        print_status "$GREEN" "- stock-analysis-controller.sh: Executable"
        # Test execution (dry run)
        "$SCRIPT_DIR/stock-analysis-controller.sh" daily --dry-run >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            print_status "$GREEN" "- stock-analysis-controller.sh: Test passed"
        else
            print_status "$RED" "- stock-analysis-controller.sh: Test failed"
        fi
    else
        print_status "$RED" "- stock-analysis-controller.sh: Not executable"
    fi
    
    # Test weekly report generator
    if [ -x "$SCRIPT_DIR/cron-weekly-report.sh" ]; then
        print_status "$GREEN" "- cron-weekly-report.sh: Executable"
    else
        print_status "$RED" "- cron-weekly-report.sh: Not executable"
    fi
}

# Main installation process
main() {
    print_status "$YELLOW" "Installing Stock Analysis Cron Jobs..."
    echo
    
    # Create log directory
    create_log_directory
    echo
    
    # Test scripts
    test_scripts
    echo
    
    # Add daily cron job (9:00 AM every day)
    add_cron_job "0 9 * * *" "$SCRIPT_DIR/stock-analysis-controller.sh daily" "Daily stock analysis"
    echo
    
    # Add weekly cron job (10:00 AM every Saturday)
    add_cron_job "0 10 * * 6" "$SCRIPT_DIR/stock-analysis-controller.sh weekly" "Weekly stock report"
    echo
    
    # Display current crontab
    print_status "$YELLOW" "Current crontab:"
    crontab -l 2>/dev/null || print_status "$RED" "No crontab found"
    echo
    
    # Display next run times
    print_status "$YELLOW" "Next scheduled runs:"
    echo "- Daily analysis: $(date -d 'tomorrow 09:00' '+%Y-%m-%d %H:%M')"
    echo "- Weekly report: $(date -d 'next Saturday 10:00' '+%Y-%m-%d %H:%M')"
    echo
    
    print_status "$GREEN" "Installation completed!"
    echo
    print_status "$YELLOW" "Cron jobs will now run automatically:"
    echo "- Daily: Every day at 9:00 AM"
    echo "- Weekly: Every Saturday at 10:00 AM"
    echo
    print_status "$YELLOW" "Log files will be stored in: $LOG_DIR"
    print_status "$YELLOW" "Reports will be stored in: $SCRIPT_DIR/reports/"
}

# Execute main function
main "$@"