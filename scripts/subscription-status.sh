#!/usr/bin/env bash
# subscription-status.sh — Quick view of Athanor subscription burn state
# Usage: subscription-status.sh [status|waste|schedule|tasks <sub>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

API="${SUBSCRIPTION_BURN_URL}"
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

cmd="${1:-status}"

check_service() {
    if ! curl -sf "$API/health" > /dev/null 2>&1; then
        echo -e "${RED}Subscription Burn not running on :8065${NC}"
        echo ""
        echo "Falling back to process check..."
        echo ""
        echo -e "${BOLD}Running AI CLI processes:${NC}"
        ps aux 2>/dev/null | grep -E '(claude|codex|gemini|kimi) ' | grep -v grep || echo "  (none)"
        exit 1
    fi
}

fmt_pct() {
    local pct=$1
    if [ "$pct" -ge 75 ]; then
        echo -e "${GREEN}${pct}%${NC}"
    elif [ "$pct" -ge 40 ]; then
        echo -e "${YELLOW}${pct}%${NC}"
    else
        echo -e "${RED}${pct}%${NC}"
    fi
}

case "$cmd" in
    status)
        check_service
        echo -e "${BOLD}=== Athanor Subscription Burn Status ===${NC}"
        echo ""
        data=$(curl -sf "$API/status")
        total=$(echo "$data" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_monthly_cost'])")
        echo -e "${CYAN}Total monthly cost: \$${total}${NC}"
        echo ""
        printf "%-20s %-15s %-10s %-12s %s\n" "SUBSCRIPTION" "TYPE" "UTIL" "COST/MO" "STATUS"
        printf "%-20s %-15s %-10s %-12s %s\n" "------------" "----" "----" "-------" "------"
        echo "$data" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for name, info in data['subscriptions'].items():
    stype = info.get('type', '?')[:13]
    pct = info.get('utilization_pct', '-')
    cost = info.get('cost_per_month', 0)
    running = 'RUNNING' if info.get('running') else 'idle'
    pct_str = f'{pct}%' if isinstance(pct, int) else str(pct)
    print(f'{name:<20} {stype:<15} {pct_str:<10} \${cost:<11} {running}')
"
        ;;

    waste)
        check_service
        echo -e "${BOLD}=== Waste Report ===${NC}"
        echo ""
        data=$(curl -sf "$API/waste-report")
        echo "$data" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Daily waste estimate:   \${data['total_daily_waste_est']:.2f}\")
print(f\"Monthly waste estimate: \${data['total_monthly_waste_est']:.0f}\")
print()
printf_fmt = '{:<20} {:>8} {:>10} {:>12}'
print(printf_fmt.format('SUBSCRIPTION', 'UTIL', 'DAILY', 'MONTHLY'))
print(printf_fmt.format('------------', '----', '-----', '-------'))
for name, info in data['subscriptions'].items():
    pct = f\"{info['utilization_pct']}%\"
    dw = f\"\${info['daily_waste_est']:.2f}\"
    mw = f\"\${info['monthly_waste_est']:.0f}\"
    print(printf_fmt.format(name, pct, dw, mw))
"
        ;;

    schedule)
        check_service
        echo -e "${BOLD}=== Upcoming Burn Windows ===${NC}"
        echo ""
        data=$(curl -sf "$API/schedule")
        echo "$data" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for w in data['windows']:
    hrs = w['hours_until']
    label = w['label']
    subs = ', '.join(w['subscriptions'])
    time = w['time']
    print(f'  {time:>10}  ({hrs:.1f}h)  {label}')
    print(f'             subs: {subs}')
    print()
"
        ;;

    tasks)
        check_service
        sub="${2:-claude_max}"
        echo -e "${BOLD}=== Tasks: ${sub} ===${NC}"
        echo ""
        data=$(curl -sf "$API/tasks/$sub")
        echo "$data" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Task file: {data.get('task_file', 'N/A')}\")
print(f\"Total: {data['total']}  Pending: {data['pending']}  In-progress: {data['in_progress']}  Done: {data['done']}\")
print()
for t in data.get('tasks', []):
    if isinstance(t, dict):
        status = t.get('status', 'pending')
        desc = t.get('description', t.get('prompt', ''))[:80]
        icon = {'pending': ' ', 'in_progress': '>', 'done': 'x'}
        print(f\"  [{icon.get(status, '?')}] {desc}\")
"
        ;;

    *)
        echo "Usage: $0 [status|waste|schedule|tasks <subscription>]"
        exit 1
        ;;
esac
