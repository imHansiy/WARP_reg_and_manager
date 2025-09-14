#!/bin/bash

# Linux script to start Warp terminal with proxy configuration
# This ensures Warp uses the mitmproxy for account switching

# Proxy configuration
PROXY_HOST="127.0.0.1"
PROXY_PORT="8080"
PROXY_URL="http://${PROXY_HOST}:${PROXY_PORT}"

# Common Warp terminal paths on Linux
WARP_PATHS=(
    "/opt/warpdotdev/warp-terminal/warp"
    "/usr/local/bin/warp"
    "/usr/bin/warp"
    "$HOME/.local/bin/warp"
    "/snap/bin/warp"
    "/var/lib/flatpak/exports/bin/dev.warp.Warp"
    "$HOME/.local/share/flatpak/exports/bin/dev.warp.Warp"
)

echo "🚀 Starting Warp Terminal with Proxy Configuration (Linux)"
echo "========================================================"
echo "Proxy: ${PROXY_URL}"
echo
echo "ℹ️  Note: Make sure to start Warp Account Manager and enable proxy"
echo "   for account switching to work properly."
echo

# Find Warp executable
WARP_PATH=""
for path in "${WARP_PATHS[@]}"; do
    if [[ -f "$path" && -x "$path" ]]; then
        WARP_PATH="$path"
        echo "✅ Warp terminal found: $WARP_PATH"
        break
    fi
done

if [[ -z "$WARP_PATH" ]]; then
    echo "❌ ERROR: Warp terminal not found in any of these locations:"
    printf "   - %s\n" "${WARP_PATHS[@]}"
    echo
    echo "   Please install Warp or update the WARP_PATHS array in this script"
    echo "   Installation methods:"
    echo "   - Download from: https://www.warp.dev/"
    echo "   - Or find warp executable: which warp"
    exit 1
fi

echo
echo "🔄 Starting Warp with proxy environment variables..."
echo "   Warp will use proxy: ${PROXY_URL}"
echo "   Start Warp Account Manager proxy for account switching"
echo

# Export proxy environment variables and start Warp
export http_proxy="${PROXY_URL}"
export https_proxy="${PROXY_URL}"
export HTTP_PROXY="${PROXY_URL}"
export HTTPS_PROXY="${PROXY_URL}"

# Start Warp with proxy configuration
echo "Executing: $WARP_PATH $*"
exec "$WARP_PATH" "$@"