#!/bin/bash
# Cross-platform notification helper
# Usage: bash notify.sh "Title" "Message" [duration_ms]
# Works on: Windows (PowerShell toast), Linux (notify-send), macOS (osascript)

TITLE="${1:-Claude Code}"
MESSAGE="${2:-Notification}"
DURATION="${3:-5000}"

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    # Windows: PowerShell toast via WinRT
    powershell -NoProfile -Command "
      [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
      [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null
      \$template = @'
<toast duration='short'>
  <visual>
    <binding template='ToastGeneric'>
      <text>$TITLE</text>
      <text>$MESSAGE</text>
    </binding>
  </visual>
</toast>
'@
      \$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
      \$xml.LoadXml(\$template)
      \$toast = [Windows.UI.Notifications.ToastNotification]::new(\$xml)
      [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Claude Code').Show(\$toast)
    " 2>/dev/null || true
    ;;
  Linux*)
    notify-send -t "$DURATION" "$TITLE" "$MESSAGE" 2>/dev/null || true
    ;;
  Darwin*)
    osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\"" 2>/dev/null || true
    ;;
esac
