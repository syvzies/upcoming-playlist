#!/bin/bash

# Activate virtual environment
source "$(dirname "$0")/upcomingplaylist/bin/activate"

# Set Spotify credentials
# Replace these with your actual values
export SPOTIFY_PLAYLIST_ID="65Rp5V4nh7QOLma3M3ERsC"

# Run the script with all arguments passed to this script
python "$(dirname "$0")/main.py" "$@"
