#!/bin/zsh
# Opens the local application and starts macOS's built-in three-minute screen recorder.
# Before recording, enable your camera overlay in the macOS recording controls or use
# QuickTime/OBS picture-in-picture. Do not show .env, terminals, or API keys.
set -e
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
OUTPUT="$HOME/Desktop/Lenny Growth Assistant Demo.mov"

open "http://127.0.0.1:3000"
echo "The app is opening in your browser."
echo "In the macOS capture toolbar, select the Lenny browser window, enable microphone and camera overlay, then click Record."
echo "Recording stops automatically after three minutes and saves to: $OUTPUT"
sleep 3
screencapture -v -g -k -V180 -P "$OUTPUT"
