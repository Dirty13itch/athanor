#!/usr/bin/env bash
# Setup WireGuard VPN on UDM Pro for remote mobile access
# Usage: ./setup-wireguard-vpn.sh <udm-username> <udm-password>
#
# This script:
# 1. Authenticates to the UDM Pro local API
# 2. Creates a WireGuard VPN server (10.10.10.0/24)
# 3. Creates a phone client profile
# 4. Outputs the WireGuard config for import into the phone app

set -euo pipefail

UDM_HOST="https://192.168.1.1"
UDM_USER="${1:?Usage: $0 <username> <password>}"
UDM_PASS="${2:?Usage: $0 <username> <password>}"
CLIENT_NAME="shaun-phone"
VPN_SUBNET="10.10.10.1/24"
VPN_PORT=51820
DNS_SERVER="192.168.1.1"

COOKIE_JAR=$(mktemp)
trap "rm -f $COOKIE_JAR" EXIT

echo "=== Authenticating to UDM Pro ==="
AUTH_RESP=$(curl -sk -X POST "$UDM_HOST/api/auth/login" \
  -H "Content-Type: application/json" \
  -c "$COOKIE_JAR" \
  -d "{\"username\":\"$UDM_USER\",\"password\":\"$UDM_PASS\"}" \
  -w "\n%{http_code}")

AUTH_CODE=$(echo "$AUTH_RESP" | tail -1)
if [ "$AUTH_CODE" != "200" ]; then
  echo "Authentication failed (HTTP $AUTH_CODE)"
  echo "$AUTH_RESP" | head -5
  exit 1
fi
echo "Authenticated successfully."

# Extract CSRF token if present
CSRF_TOKEN=$(curl -sk -b "$COOKIE_JAR" "$UDM_HOST/proxy/network/" -o /dev/null -D - 2>/dev/null | grep -i 'x-csrf-token' | awk '{print $2}' | tr -d '\r' || true)

HEADERS=(-H "Content-Type: application/json" -b "$COOKIE_JAR")
if [ -n "$CSRF_TOKEN" ]; then
  HEADERS+=(-H "X-CSRF-Token: $CSRF_TOKEN")
fi

echo ""
echo "=== Checking existing VPN servers ==="
EXISTING=$(curl -sk "${HEADERS[@]}" "$UDM_HOST/proxy/network/v2/api/vpn/server" 2>&1)
echo "$EXISTING" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    servers = d if isinstance(d, list) else d.get('data',[])
    if servers:
        print(f'Found {len(servers)} existing VPN server(s):')
        for s in servers:
            print(f'  - {s.get(\"name\",\"?\")} ({s.get(\"vpn_type\",\"?\")}): {s.get(\"server_address\",\"?\")}')
    else:
        print('No existing VPN servers.')
except Exception as e:
    print(f'Could not parse response: {e}')
    print(sys.stdin.read()[:200] if hasattr(sys.stdin,'read') else str(d)[:200])
" 2>&1

echo ""
echo "=== Creating WireGuard VPN Server ==="
echo "(If this fails, the API endpoint may differ on your firmware version)"

# Try the v2 API first (newer firmware)
CREATE_RESP=$(curl -sk -X POST "${HEADERS[@]}" \
  "$UDM_HOST/proxy/network/v2/api/vpn/server" \
  -d "{
    \"name\": \"athanor-mobile\",
    \"vpn_type\": \"wireguard-server\",
    \"x_wireguard_enabled\": true,
    \"x_wg_port\": $VPN_PORT,
    \"server_address\": \"$VPN_SUBNET\",
    \"x_dns_1\": \"$DNS_SERVER\"
  }" \
  -w "\n%{http_code}" 2>&1)

CREATE_CODE=$(echo "$CREATE_RESP" | tail -1)
CREATE_BODY=$(echo "$CREATE_RESP" | sed '$d')

if [ "$CREATE_CODE" = "200" ] || [ "$CREATE_CODE" = "201" ]; then
  echo "WireGuard server created successfully!"
  SERVER_ID=$(echo "$CREATE_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('_id',d.get('id','')))" 2>/dev/null)
  echo "Server ID: $SERVER_ID"
else
  echo "v2 API failed (HTTP $CREATE_CODE). Trying alternative endpoints..."
  echo "Response: $CREATE_BODY" | head -5

  # Try v1 API
  CREATE_RESP=$(curl -sk -X POST "${HEADERS[@]}" \
    "$UDM_HOST/proxy/network/api/s/default/rest/vpnserver" \
    -d "{
      \"name\": \"athanor-mobile\",
      \"vpn_type\": \"wireguard-server\",
      \"x_wireguard_enabled\": true,
      \"x_wg_port\": $VPN_PORT,
      \"server_address\": \"$VPN_SUBNET\"
    }" \
    -w "\n%{http_code}" 2>&1)

  CREATE_CODE=$(echo "$CREATE_RESP" | tail -1)
  CREATE_BODY=$(echo "$CREATE_RESP" | sed '$d')

  if [ "$CREATE_CODE" = "200" ] || [ "$CREATE_CODE" = "201" ]; then
    echo "WireGuard server created via v1 API!"
    SERVER_ID=$(echo "$CREATE_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); data=d.get('data',[]); print(data[0].get('_id','') if data else '')" 2>/dev/null)
  else
    echo "Both API attempts failed. Response:"
    echo "$CREATE_BODY" | head -10
    echo ""
    echo "Your firmware may not support WireGuard via API."
    echo "Manual setup: Settings > VPN > VPN Server > Create New > WireGuard"
    echo "  Server Address: $VPN_SUBNET"
    echo "  Port: $VPN_PORT"
    echo "  DNS: $DNS_SERVER"
    exit 1
  fi
fi

echo ""
echo "=== Creating Client Profile ==="
if [ -n "$SERVER_ID" ]; then
  CLIENT_RESP=$(curl -sk -X POST "${HEADERS[@]}" \
    "$UDM_HOST/proxy/network/v2/api/vpn/server/$SERVER_ID/clients" \
    -d "{\"name\": \"$CLIENT_NAME\"}" \
    -w "\n%{http_code}" 2>&1)

  CLIENT_CODE=$(echo "$CLIENT_RESP" | tail -1)
  CLIENT_BODY=$(echo "$CLIENT_RESP" | sed '$d')

  if [ "$CLIENT_CODE" = "200" ] || [ "$CLIENT_CODE" = "201" ]; then
    echo "Client profile created!"
    echo ""
    echo "=== WireGuard Config ==="
    echo "$CLIENT_BODY" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    config = d.get('wg_config', d.get('configuration', ''))
    if config:
        print(config)
    else:
        print(json.dumps(d, indent=2))
except:
    print(sys.stdin.read() if hasattr(sys.stdin,'read') else str(d))
" 2>&1
  else
    echo "Client creation returned HTTP $CLIENT_CODE"
    echo "$CLIENT_BODY" | head -10
    echo ""
    echo "Try creating the client through the web UI:"
    echo "Settings > VPN > VPN Server > athanor-mobile > Add Client"
  fi
else
  echo "No server ID available. Create client manually in the web UI."
fi

echo ""
echo "=== Next Steps ==="
echo "1. Copy the WireGuard config above (or scan QR from UDM Pro UI)"
echo "2. Import into WireGuard app on your phone"
echo "3. Enable 'Always On VPN' in phone settings"
echo "4. Open http://192.168.1.225:3001 and add to home screen"
echo ""
echo "Direct connect domain: $(curl -sk $UDM_HOST/api/system 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get(\"directConnectDomain\",\"unknown\"))' 2>/dev/null)"
