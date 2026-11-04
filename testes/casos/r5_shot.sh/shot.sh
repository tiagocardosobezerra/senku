#!/bin/bash
# shot.sh file.svg out.png [w h]
IN=$(cygpath -w "$(realpath "$1")"); OUT=$(cygpath -w "$(realpath -m "$2")")
W=${3:-1400}; H=${4:-900}
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --disable-gpu --hide-scrollbars --user-data-dir="$TEMP\edgeshot" --window-size=$W,$H --screenshot="$OUT" "file:///${IN//\//}" >/dev/null 2>&1
ls -la "$2"
