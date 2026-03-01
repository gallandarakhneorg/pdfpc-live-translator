#!/usr/bin/env bash

PYTHON_VIRTUAL_ENV="/usr"

DIR=`pwd`

# Launch pdfpc in the background
"$DIR/start_talk.sh" "$@" &
PDFPC_PID=$!

# Give pdfpc time to open and go fullscreen
sleep 2

# Launch the Tkinter overlay
"$PYTHON_VIRTUAL_ENV/bin/python3" "$DIR/live-translator.py" &
OVERLAY_PID=$!

# Wait for pdfpc to exit, then kill the overlay too
wait $PDFPC_PID
kill $OVERLAY_PID 2>/dev/null
