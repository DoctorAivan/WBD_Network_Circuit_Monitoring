#!/bin/bash
# --------------------------------------------
# WBD_Network_Circuit_Monitoring
# Monitors the "logs" folder and sends modified files
# to the Django endpoint via POST.
# --------------------------------------------

# CONFIGURATION
# LOG_DIR="/Volumes/SSD1/dev/WM_tntsports_2025/WBD_logs_tracking/backend/logs"
LOG_DIR="/tmp/circuits-status/logs"

API_URL="https://circuits-status.net.wbd.com/api/logs-add/"
API_KEY="123456789TOKEN"
CONTENT_TYPE="text/plain"
SCRIPT_LOG="/home/ivillarroel_sso/apps/WBD_Network_Circuit_Monitoring/log_uploader.log"

echo "# Starting log monitor #"

# Send file to API
send_file() {

    # Create file path
    local FILE_PATH="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Sending file $FILE_PATH" >> "$SCRIPT_LOG"

    # Validate that the file has content
    if [[ ! -s "$FILE_PATH" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] Empty file: $FILE_PATH" >> "$SCRIPT_LOG"
        return
    fi

    # Create API request
    curl -s -X POST "$API_URL" \
        -H "Content-Type: $CONTENT_TYPE" \
        -H "Authorization: Bearer $API_KEY" \
        --data-binary @"$FILE_PATH" \
        -o /dev/null -w "%{http_code}" | {
            read status
            if [[ "$status" == "200" ]]; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] Successful shipment: $FILE_PATH" >> "$SCRIPT_LOG"
            else
                echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] Sending failed ($status): $FILE_PATH" >> "$SCRIPT_LOG"
            fi
        }
}
# LINUX - Use inotifywait to listen for changes in logs directory
inotifywait -m -e close_write,create,modify "$LOG_DIR" --format '%w%f' | while read FILE
do
    # Only read txt files
    if [[ "$FILE" == *.tmp ]]; then
        send_file "$FILE"
    fi
done