#!/bin/bash

# Activate virtual environment
source "$(dirname "$0")/upcomingplaylist/bin/activate"

# Set Spotify credentials
# Replace these with your actual values
export SPOTIFY_CLIENT_ID="d2776941818f424b9153f1ef3844d13c"
export SPOTIFY_CLIENT_SECRET="d70b2d04c69f4d49ad9318488d98b7d4" 
export SPOTIFY_PLAYLIST_ID="65Rp5V4nh7QOLma3M3ERsC"

# Run the script with all arguments passed to this script
python "$(dirname "$0")/main.py" "$@"