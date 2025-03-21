# Upcoming Playlist

A simple web app that lets you scrape the calendar for certain venues to create a Spotify playlist of the most popular songs of the artists that are playing at the venues near you.

## Features

- Scrape artist names from venue websites
- Search for artists on Spotify
- Add artists' top tracks to a Spotify playlist
- Create a new playlist or add to an existing one
- Works entirely in the browser (no server required)

## Setup Instructions

1. Clone this repository:
   ```
   git clone https://github.com/syvzies/upcoming-playlist.git
   cd upcoming-playlist
   ```

2. Create a Spotify Developer Application:
   - Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Log in with your Spotify account
   - Click "Create App"
   - Fill in the application details:
     - App name: Upcoming Playlist (or your preferred name)
     - App description: A web app that creates playlists from venue calendars
     - Redirect URI: http://localhost:8080/callback (or your preferred URL with /callback at the end)
     - Website: (optional)
   - Accept the terms and click "Create"

3. Get your Client ID:
   - After creating the app, you'll be taken to your app's dashboard
   - Copy the "Client ID" - you'll need this for the application

4. Update the application:
   - Open `app.js` in your text editor
   - Replace `YOUR_SPOTIFY_CLIENT_ID` with your actual Client ID:
     ```javascript
     const SPOTIFY_CLIENT_ID = 'your-client-id-here';
     ```

5. Set up CORS Proxy:
   - Due to browser security restrictions, you'll need a CORS proxy to scrape venue websites
   - The app is configured to use the public CORS Anywhere service
   - For development, visit https://cors-anywhere.herokuapp.com/corsdemo and request temporary access
   - For production, consider setting up your own CORS proxy

6. Run the application:
   - You can run the app using a simple HTTP server
   - If you have Python installed:
     ```
     # Python 3
     python -m http.server 8080
     
     # Python 2
     python -m SimpleHTTPServer 8080
     ```
   - Or use any other HTTP server of your choice
   - Open your browser and navigate to http://localhost:8080

## Usage

1. Connect to Spotify:
   - Click the "Connect Spotify" button
   - Log in with your Spotify account and authorize the application

2. Enter venue information:
   - Paste the URL of a venue's schedule page
   - Adjust the CSS selector if needed (the default works for Bandsintown)
   - Click "Find Artists"

3. Add to playlist:
   - Review the artists and tracks found
   - Select an existing playlist or create a new one
   - Click "Add Tracks to Playlist"

## How It Works

1. **Venue Scraping**:
   - The app uses a CORS proxy to fetch the HTML from venue websites
   - It parses the HTML and extracts artist names using the provided CSS selector

2. **Spotify Integration**:
   - The app uses the Spotify Web API to search for artists
   - For each artist, it retrieves their top 2 tracks
   - It can create playlists or add tracks to existing ones

3. **Authentication**:
   - Authentication is handled using OAuth 2.0 Implicit Grant flow
   - No server is required as all authentication happens in the browser

## Limitations

- **CORS Restrictions**: Due to browser security, a CORS proxy is required to access venue websites
- **CSS Selectors**: You need to find the correct CSS selector for each venue's website
- **Rate Limiting**: The Spotify API has rate limits that may affect large requests

## License

MIT License - See LICENSE file for details