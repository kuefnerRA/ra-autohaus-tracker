# RA Autohaus Tracker - Clean Bash Additions
# Add this to your ~/.bashrc with: source ~/dev/ra-autohaus-tracker/scripts/bashrc_additions.sh

# Environment
export RA_PROJECT="ra-autohaus-tracker"
export RA_SERVICE="ra-autohaus-tracker"
export RA_API_URL="https://ra-autohaus-tracker-p6yblocfea-ey.a.run.app"
export RA_SCRIPTS="$HOME/dev/ra-autohaus-tracker/scripts"

# Development shortcuts
alias ra-setup='source ~/dev/ra-autohaus-tracker/scripts/setup-dev.sh'
alias ra-server='python -m src.main'
alias ra-logs='tail -f ~/dev/ra-autohaus-tracker/logs/server.log'

# Monitoring aliases
alias ra-monitor='$RA_SCRIPTS/ra-monitor.sh monitor'
alias ra-monitor-fin='$RA_SCRIPTS/ra-monitor.sh monitor-fin'
alias ra-monitor-pretty='$RA_SCRIPTS/ra-monitor.sh pretty'
alias ra-errors='$RA_SCRIPTS/ra-monitor.sh errors'
alias ra-requests='$RA_SCRIPTS/ra-monitor.sh requests'

# Testing aliases
alias ra-test='$RA_SCRIPTS/ra-test.sh suite'
alias ra-test-endpoint='$RA_SCRIPTS/ra-test.sh endpoint'
alias ra-check-fin='$RA_SCRIPTS/ra-test.sh fin'
alias ra-test-zapier='$RA_SCRIPTS/ra-test.sh zapier'
alias ra-test-email='$RA_SCRIPTS/ra-test.sh email'
alias ra-endpoints='$RA_SCRIPTS/ra-test.sh endpoints'

# Environment aliases
alias ra-use-local='source $RA_SCRIPTS/ra-env.sh local'
alias ra-use-prod='source $RA_SCRIPTS/ra-env.sh prod'
alias ra-config='$RA_SCRIPTS/ra-env.sh show'
alias ra-health='$RA_SCRIPTS/ra-env.sh health'

# Quick access to scripts directory
alias ra-scripts='cd $RA_SCRIPTS'

echo "✅ RA Autohaus Tracker environment loaded"
echo "   Use 'ra-config' to see current configuration"
echo "   Use 'ra-test' to run API tests"
echo "   Use 'ra-monitor' to watch logs"
