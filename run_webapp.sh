#!/bin/bash

# Check if Redis is installed and running
if command -v redis-cli &>/dev/null; then
    echo "Checking Redis status..."
    if ! redis-cli ping &>/dev/null; then
        echo "Redis is not running. Attempting to start Redis..."
        if command -v redis-server &>/dev/null; then
            redis-server --daemonize yes
        else
            echo "Redis server not found. Please install Redis:" 
            echo "sudo apt install redis-server"
            exit 1
        fi
    else
        echo "Redis is running."
    fi
else
    echo "Redis-cli not found. Please install Redis:"
    echo "sudo apt install redis-server"
    exit 1
fi

# Activate virtual environment
source "$(dirname "$0")/upcomingplaylist/bin/activate"

# Make sure dependencies are installed
pip install -r "$(dirname "$0")/requirements.txt"

# Set Spotify credentials
# Replace these with your actual values
export SPOTIFY_CLIENT_ID="d2776941818f424b9153f1ef3844d13c"
export SPOTIFY_CLIENT_SECRET="d70b2d04c69f4d49ad9318488d98b7d4" 
export SPOTIFY_PLAYLIST_ID="65Rp5V4nh7QOLma3M3ERsC"

# Redirect URI for web authentication (must match exactly in your Spotify Dashboard settings)
export SPOTIFY_REDIRECT_URI="http://localhost:5000/callback"

# Set Flask secret key (change this to a random string for security)
export FLASK_SECRET_KEY="change_this_to_a_random_secure_string"

# Run the Flask app
python "$(dirname "$0")/web_app.py"