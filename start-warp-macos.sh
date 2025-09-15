#!/bin/bash

# macOS script to start Warp terminal with proxy configuration
# This ensures Warp uses the mitmproxy for account switching

# Proxy configuration
PROXY_HOST="127.0.0.1"
PROXY_PORT="8080"
PROXY_URL="http://${PROXY_HOST}:${PROXY_PORT}"

# Common Warp terminal paths on macOS
WARP_PATHS=(
    "/Applications/Warp.app/Contents/MacOS/Warp"
    "/Applications/Warp.app"
    "/usr/local/bin/warp"
    "/opt/homebrew/bin/warp"
    "/usr/bin/warp"
    "$HOME/.local/bin/warp"
    "$HOME/Applications/Warp.app/Contents/MacOS/Warp"
    "$HOME/Applications/Warp.app"
)

echo "🚀 Starting Warp Terminal with Proxy Configuration (macOS)"
echo "========================================================="
echo "Proxy: ${PROXY_URL}"
echo
echo "ℹ️  Note: Make sure to start Warp Account Manager and enable proxy"
echo "   for account switching to work properly."
echo

# Find Warp executable
WARP_PATH=""
for path in "${WARP_PATHS[@]}"; do
    if [[ -d "$path" && "$path" == *".app" ]]; then
        # For .app bundles, check if we can open them
        if [[ -d "$path" ]]; then
            WARP_PATH="$path"
            echo "✅ Warp application bundle found: $WARP_PATH"
            break
        fi
    elif [[ -f "$path" && -x "$path" ]]; then
        WARP_PATH="$path"
        echo "✅ Warp executable found: $WARP_PATH"
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
    echo "   - Install via Homebrew: brew install --cask warp"
    echo "   - Or find warp executable: which warp"
    exit 1
fi

echo
echo "🔄 Starting Warp with proxy environment variables..."
echo "   Warp will use proxy: ${PROXY_URL}"
echo "   Start Warp Account Manager proxy for account switching"
echo

# Export proxy environment variables
export http_proxy="${PROXY_URL}"
export https_proxy="${PROXY_URL}"
export HTTP_PROXY="${PROXY_URL}"
export HTTPS_PROXY="${PROXY_URL}"

# Start Warp with proxy configuration
if [[ "$WARP_PATH" == *".app" ]]; then
    # Use 'open' command for .app bundles on macOS
    echo "Executing: open \"$WARP_PATH\" --args $*"
    exec open "$WARP_PATH" --args "$@"
else
    # Direct executable path
    echo "Executing: $WARP_PATH $*"
    exec "$WARP_PATH" "$@"
fi
