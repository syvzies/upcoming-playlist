#!/usr/bin/env python3
import os
import logging
import uuid
import redis
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_session import Session
from scraper import get_upcoming_artists
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-key-for-testing-only')

# Configure server-side session, preferring Redis but falling back to filesystem
try:
    # Try to connect to Redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.ping()  # This will raise an exception if Redis is not available
    
    logger.info("Using Redis for session storage")
    app.config["SESSION_TYPE"] = "redis"
    app.config["SESSION_REDIS"] = redis_client
except Exception as e:
    # If Redis is not available, fall back to filesystem
    logger.warning(f"Redis not available ({str(e)}), falling back to filesystem session")
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = "/tmp/flask_session"
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

app.config["SESSION_PERMANENT"] = True  # Make sessions last longer
app.config["SESSION_USE_SIGNER"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 2  # 2 hours in seconds
Session(app)

# Default CSS selector for the venue website
DEFAULT_SELECTOR = "div.wPBHIIJzw9ltGDuXqcAD"

# Spotify configuration
CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:5000/callback')
# Include all necessary scopes for playlist manipulation
SCOPE = "playlist-modify-public playlist-modify-private user-library-read user-read-email"

# Check if Spotify credentials are configured
SPOTIFY_CONFIGURED = all([CLIENT_ID, CLIENT_SECRET])

def get_spotify_oauth():
    """Create a SpotifyOAuth instance with the correct redirect URI for web."""
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=None  # Don't use file cache
    )

def get_spotify_client():
    """Get a Spotify client using the current user's auth token."""
    if not SPOTIFY_CONFIGURED:
        return None
        
    # Check if user has a token in the session
    if 'spotify_token_info' not in session:
        return None
        
    # Create a Spotify client with the token
    token_info = session['spotify_token_info']
    return spotipy.Spotify(auth=token_info['access_token'])

def get_user_playlists(sp):
    """Get all playlists owned by or collaborative with the current user."""
    try:
        # Get current user's info
        current_user = sp.current_user()
        user_id = current_user['id']
        logger.info(f"Fetching playlists for Spotify user: {user_id}")
        
        # Get all user's playlists
        playlists = []
        results = sp.current_user_playlists(limit=50)
        
        while results:
            items = results['items']
            for item in items:
                # Only include playlists the user can modify 
                # (owned by user or collaborative)
                if item['owner']['id'] == user_id or item.get('collaborative', False):
                    playlists.append({
                        'id': item['id'],
                        'name': item['name'],
                        'owner': item['owner']['display_name'],
                        'public': item['public'],
                        'collaborative': item.get('collaborative', False),
                        'tracks_total': item['tracks']['total']
                    })
            
            if results['next']:
                results = sp.next(results)
            else:
                results = None
        
        logger.info(f"Found {len(playlists)} playlists that the user can modify")
        return playlists
    except Exception as e:
        logger.error(f"Error fetching user playlists: {e}")
        return []

def check_playlist_permissions(sp, playlist_id):
    """Check if the authenticated user has permission to modify the given playlist."""
    if not playlist_id:
        logger.warning("No playlist ID provided")
        return False
        
    try:
        # Get current user's info
        current_user = sp.current_user()
        user_id = current_user['id']
        logger.info(f"Authenticated as Spotify user: {user_id}")
        
        # Get playlist info
        playlist = sp.playlist(playlist_id)
        playlist_owner = playlist['owner']['id']
        playlist_name = playlist['name']
        is_public = playlist['public']
        is_collaborative = playlist.get('collaborative', False)
        
        logger.info(f"Playlist: {playlist_name} (ID: {playlist_id})")
        logger.info(f"Playlist owner: {playlist_owner}, Current user: {user_id}")
        logger.info(f"Playlist is public: {is_public}, collaborative: {is_collaborative}")
        
        # Check if user is the owner or the playlist is collaborative
        if user_id == playlist_owner:
            logger.info("User is the playlist owner - has full permissions")
            return True
        elif is_collaborative:
            logger.info("Playlist is collaborative - user can modify")
            return True
        else:
            logger.warning("User does not have permission to modify this playlist")
            return False
    except Exception as e:
        logger.error(f"Error checking playlist permissions: {e}")
        return False

def search_artist(sp, artist_name):
    """Search for an artist on Spotify and return their ID."""
    try:
        logger.info(f"Searching for artist: {artist_name}")
        results = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
        
        if results['artists']['items']:
            artist = results['artists']['items'][0]
            logger.info(f"Found artist: {artist['name']} (ID: {artist['id']})")
            return artist['id']
        else:
            logger.warning(f"No artist found for: {artist_name}")
            return None
    except Exception as e:
        logger.error(f"Error searching for artist {artist_name}: {e}")
        return None

def get_top_tracks(sp, artist_id, limit=2):
    """Get the top tracks for an artist."""
    try:
        logger.info(f"Fetching top {limit} tracks for artist ID: {artist_id}")
        results = sp.artist_top_tracks(artist_id)
        
        tracks = []
        for track in results['tracks'][:limit]:
            track_info = {
                'id': track['id'],
                'name': track['name'],
                'album': track['album']['name'],
                'uri': track['uri']
            }
            tracks.append(track_info)
            logger.info(f"Found track: {track['name']} from album {track['album']['name']}")
        
        return tracks
    except Exception as e:
        logger.error(f"Error getting top tracks for artist {artist_id}: {e}")
        return []

def clear_playlist(sp, playlist_id):
    """Remove all tracks from the specified playlist."""
    if not playlist_id:
        logger.warning("No playlist ID provided")
        return False
        
    try:
        logger.info(f"Removing all tracks from playlist ID: {playlist_id}")
        
        # First check if the playlist exists
        try:
            playlist_info = sp.playlist(playlist_id)
            logger.info(f"Found playlist: {playlist_info['name']} (ID: {playlist_id})")
        except Exception as playlist_error:
            logger.error(f"Error accessing playlist ID {playlist_id}: {playlist_error}")
            return False
            
        # Get all tracks in the playlist
        all_tracks = []
        results = sp.playlist_items(playlist_id, fields='items(track(uri)),next', limit=100)
        
        while results:
            for item in results['items']:
                if item['track'] and 'uri' in item['track']:
                    all_tracks.append(item['track']['uri'])
            
            if results['next']:
                results = sp.next(results)
            else:
                break
                
        if not all_tracks:
            logger.info("Playlist is already empty")
            return True
            
        logger.info(f"Found {len(all_tracks)} tracks to remove")
        
        # Spotify API can only remove 100 tracks at a time
        chunk_size = 100
        for i in range(0, len(all_tracks), chunk_size):
            chunk = all_tracks[i:i+chunk_size]
            logger.info(f"Removing chunk of {len(chunk)} tracks (items {i} to {i+len(chunk)-1})")
            try:
                # Create list of dictionaries for each track
                tracks_to_remove = [{"uri": track_uri} for track_uri in chunk]
                sp.playlist_remove_all_occurrences_of_items(playlist_id, chunk)
                logger.info(f"Successfully removed chunk of {len(chunk)} tracks")
            except Exception as chunk_error:
                logger.error(f"Error removing chunk of tracks: {chunk_error}")
                return False
        
        logger.info("Successfully removed all tracks from playlist")
        return True
    except Exception as e:
        logger.error(f"Error clearing playlist: {e}")
        return False

def add_tracks_to_playlist(sp, playlist_id, track_uris):
    """Add tracks to the specified playlist."""
    if not track_uris:
        logger.warning("No tracks to add to playlist")
        return False
        
    if not playlist_id:
        logger.warning("No playlist ID provided")
        return False
    
    try:
        logger.info(f"Adding {len(track_uris)} tracks to playlist ID: {playlist_id}")
        # Add detailed logging
        logger.info(f"First few track URIs: {track_uris[:3]}")
        
        # Check if playlist exists
        try:
            playlist_info = sp.playlist(playlist_id)
            logger.info(f"Found playlist: {playlist_info['name']} (ID: {playlist_id})")
        except Exception as playlist_error:
            logger.error(f"Error accessing playlist ID {playlist_id}: {playlist_error}")
            return False
        
        # First, check if any of these tracks are already in the playlist
        # This helps avoid potential duplicates that could cause errors
        try:
            existing_tracks = set()
            playlist_items = sp.playlist_items(playlist_id, fields='items(track(uri))', limit=100)
            
            while playlist_items:
                for item in playlist_items['items']:
                    if item['track'] and 'uri' in item['track']:
                        existing_tracks.add(item['track']['uri'])
                
                if playlist_items['next']:
                    playlist_items = sp.next(playlist_items)
                else:
                    break
                    
            logger.info(f"Found {len(existing_tracks)} existing tracks in playlist")
            
            # Filter out tracks that are already in the playlist
            new_track_uris = [uri for uri in track_uris if uri not in existing_tracks]
            if len(new_track_uris) < len(track_uris):
                logger.info(f"Filtered out {len(track_uris) - len(new_track_uris)} tracks that are already in the playlist")
                
            # If all tracks are already in the playlist, return success
            if not new_track_uris:
                logger.info("All tracks are already in the playlist")
                return True
                
            track_uris = new_track_uris
        except Exception as e:
            logger.warning(f"Error checking for existing tracks: {e}. Will proceed with all tracks.")
        
        # Spotify API limits to 100 tracks per request, so chunk them
        chunk_size = 100
        for i in range(0, len(track_uris), chunk_size):
            chunk = track_uris[i:i+chunk_size]
            logger.info(f"Adding chunk of {len(chunk)} tracks (items {i} to {i+len(chunk)-1})")
            try:
                response = sp.playlist_add_items(playlist_id, chunk)
                logger.info(f"Successfully added chunk of {len(chunk)} tracks. Response: {response}")
            except Exception as chunk_error:
                logger.error(f"Error adding chunk of tracks: {chunk_error}")
                return False
        
        logger.info("Successfully added all tracks to playlist")
        return True
    except Exception as e:
        logger.error(f"Error adding tracks to playlist: {e}")
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    """Home page with form to enter venue URL."""
    if request.method == 'POST':
        # Check if user is authenticated with Spotify
        if not SPOTIFY_CONFIGURED or 'spotify_token_info' not in session:
            flash('You must connect to Spotify before proceeding', 'error')
            return redirect(url_for('index'))
        
        # Get form data
        url = request.form.get('url')
        
        if not url:
            flash('Please enter a URL', 'error')
            return redirect(url_for('index'))
        
        # Store in session for the results page
        session['url'] = url
        session['selector'] = DEFAULT_SELECTOR
        
        # Redirect to results page
        return redirect(url_for('results'))
    
    # Check if Spotify is authenticated
    spotify_auth_url = None
    user_playlists = []
    
    if SPOTIFY_CONFIGURED:
        if 'spotify_token_info' not in session:
            # Generate a state parameter to prevent CSRF
            state = str(uuid.uuid4())
            session['spotify_auth_state'] = state
            
            # Get the authorization URL
            spotify_oauth = get_spotify_oauth()
            spotify_auth_url = spotify_oauth.get_authorize_url(state=state)
        else:
            # User is authenticated, fetch their playlists
            sp = get_spotify_client()
            if sp:
                user_playlists = get_user_playlists(sp)
                # Store playlists in session for later use
                session['user_playlists'] = user_playlists
    
    return render_template(
        'index.html', 
        spotify_configured=SPOTIFY_CONFIGURED,
        spotify_authenticated='spotify_token_info' in session,
        spotify_auth_url=spotify_auth_url,
        user_playlists=user_playlists
    )

@app.route('/callback')
def callback():
    """Handle the Spotify OAuth callback."""
    if not SPOTIFY_CONFIGURED:
        flash('Spotify credentials are not configured', 'error')
        return redirect(url_for('index'))
    
    # Check for error or code in the request
    error = request.args.get('error')
    code = request.args.get('code')
    state = request.args.get('state')
    
    if error:
        flash(f"Spotify authentication error: {error}", 'error')
        return redirect(url_for('index'))
    
    # Verify state to prevent CSRF
    stored_state = session.get('spotify_auth_state')
    if state != stored_state:
        flash("State mismatch. Please try authenticating again.", 'error')
        return redirect(url_for('index'))
    
    # Exchange code for token
    try:
        spotify_oauth = get_spotify_oauth()
        token_info = spotify_oauth.get_access_token(code, as_dict=True)
        
        # Store token in session
        session['spotify_token_info'] = token_info
        
        # Get user playlists immediately after authentication
        sp = get_spotify_client()
        if sp:
            user_playlists = get_user_playlists(sp)
            session['user_playlists'] = user_playlists
            logger.info(f"Stored {len(user_playlists)} playlists in session after authentication")
        
        flash("Successfully authenticated with Spotify!", 'success')
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        flash(f"Error authenticating with Spotify: {str(e)}", 'error')
    
    # Always redirect back to the home page after authentication
    # (Don't automatically go to results page)
    return redirect(url_for('index'))

@app.route('/results')
def results():
    """Page that shows the results of scraping and Spotify processing."""
    # Get data from session
    url = session.get('url')
    selector = session.get('selector', DEFAULT_SELECTOR)
    
    if not url:
        flash('No URL provided', 'error')
        return redirect(url_for('index'))
    
    # Check if user is authenticated with Spotify
    spotify_authenticated = SPOTIFY_CONFIGURED and 'spotify_token_info' in session
    
    # Get existing preview results if we have them
    existing_preview_results = session.get('preview_results', [])
    playlist_results = session.get('playlist_results', [])
    user_playlists = session.get('user_playlists', [])
    
    # Check if the user wants to force a new search with the reset parameter
    force_new_search = request.args.get('reset') == '1'
    if force_new_search and 'preview_results' in session:
        logger.info("Forcing a new search, clearing previous results")
        session.pop('preview_results')
        existing_preview_results = []
    
    # Only scrape and search if we don't already have results or if we explicitly want to retry
    if not existing_preview_results:
        logger.info("No existing preview results found, scraping and searching...")
        
        # Scrape artists from the venue's website
        logger.info(f"Scraping artists from {url}")
        artists = get_upcoming_artists(url, selector)
        
        if not artists:
            flash('No artists found. Please check the URL.', 'error')
            return redirect(url_for('index'))
        
        # Preview mode only shows what would be added
        preview_results = []
        
        # Get Spotify preview if authenticated
        if spotify_authenticated:
            try:
                sp = get_spotify_client()
                if sp:
                    # Ensure we have the user's playlists
                    if not user_playlists:
                        user_playlists = get_user_playlists(sp)
                        session['user_playlists'] = user_playlists
                    
                    # Just log what would be processed
                    logger.info(f"Found {len(artists)} artists that would be processed:")
                    for artist in artists:
                        artist_id = search_artist(sp, artist)
                        if artist_id:
                            top_tracks = get_top_tracks(sp, artist_id)
                            if top_tracks:
                                track_names = [f"{track['name']} ({track['album']})" for track in top_tracks]
                                preview_results.append({
                                    'name': artist,
                                    'tracks': track_names,
                                    'track_uris': [track['uri'] for track in top_tracks]
                                })
                    
                    # Store the preview results for the add-to-playlist route
                    total_uris = 0
                    for result in preview_results:
                        if 'track_uris' in result and isinstance(result['track_uris'], list):
                            total_uris += len(result['track_uris'])
                    
                    logger.info(f"Storing {len(preview_results)} artists with {total_uris} tracks in session")
                    
                    # Make a deep copy to ensure it's properly stored in the session
                    # We need to manually handle this for Flask sessions
                    preview_data = []
                    for result in preview_results:
                        name = result.get('name', '')
                        tracks = result.get('tracks', [])
                        track_uris = result.get('track_uris', [])
                        
                        # Ensure all values are properly copied
                        track_result = {
                            'name': name,
                            'tracks': list(tracks),  # Make a new list
                            'track_uris': list(track_uris)  # Make a new list
                        }
                        # Debug the structure
                        logger.info(f"Added artist: {track_result['name']} with {len(track_result['track_uris'])} track URIs")
                        
                        # Verify URIs is a proper list
                        if track_result['track_uris'] and isinstance(track_result['track_uris'], list):
                            logger.info(f"First URI: {track_result['track_uris'][0]}")
                            
                        preview_data.append(track_result)
                    
                    # Store with direct assignment (don't modify the original)
                    session['preview_results'] = preview_data
                    
                    # Save the raw artists list as well for display
                    session['artists'] = artists
            except Exception as e:
                logger.error(f"Error processing artists with Spotify: {e}")
                flash(f"Spotify Error: {str(e)}", 'error')
        
        # Use the newly created preview results
        preview_results_to_display = preview_results
        artists_to_display = artists
    else:
        # Use the existing results from session
        logger.info(f"Using existing preview results from session: {len(existing_preview_results)} artists")
        preview_results_to_display = existing_preview_results
        artists_to_display = session.get('artists', [])
    
    # Create a Spotify auth URL if needed
    spotify_auth_url = None
    if SPOTIFY_CONFIGURED and not spotify_authenticated:
        # Generate a state parameter to prevent CSRF
        state = str(uuid.uuid4())
        session['spotify_auth_state'] = state
        
        # Get the authorization URL
        spotify_oauth = get_spotify_oauth()
        spotify_auth_url = spotify_oauth.get_authorize_url(state=state)
    
    # Make sure to save all changes to the session
    session.modified = True
    
    return render_template(
        'results.html', 
        url=url,
        artists=artists_to_display,
        spotify_configured=SPOTIFY_CONFIGURED,
        spotify_authenticated=spotify_authenticated,
        spotify_auth_url=spotify_auth_url,
        preview_results=preview_results_to_display,
        playlist_results=playlist_results,
        user_playlists=user_playlists
    )

@app.route('/add-to-playlist', methods=['POST'])
def add_to_playlist():
    """Endpoint to actually add tracks to the Spotify playlist."""
    # Check if user is authenticated with Spotify
    if not SPOTIFY_CONFIGURED:
        flash('Spotify credentials are not configured', 'error')
        return redirect(url_for('results'))
    
    if 'spotify_token_info' not in session:
        flash('Please authenticate with Spotify first', 'error')
        return redirect(url_for('results'))
    
    # Get the selected playlist ID from the form
    playlist_id = request.form.get('playlist_id')
    if not playlist_id:
        flash('Please select a playlist', 'error')
        return redirect(url_for('results'))
        
    logger.info(f"Selected playlist ID: {playlist_id}")
    
    # Get preview results from session
    preview_results = session.get('preview_results', [])
    
    logger.info(f"Retrieved {len(preview_results)} artists from session")
    if preview_results:
        track_count = sum(len(artist.get('track_uris', [])) for artist in preview_results)
        logger.info(f"Found {track_count} track URIs in preview_results")
        # Log detailed info about what's in session
        for i, result in enumerate(preview_results):
            logger.info(f"Artist {i+1}: {result.get('name', 'Unknown')}")
            logger.info(f"  Tracks: {len(result.get('tracks', []))}")
            if 'track_uris' in result:
                logger.info(f"  URIs: {len(result['track_uris'])}")
                if result['track_uris']:
                    logger.info(f"  First URI: {result['track_uris'][0]}")
            else:
                logger.info("  No track_uris key found in this result")
    
    if not preview_results:
        flash('No tracks found to add to playlist. Please search for artists first.', 'warning')
        return redirect(url_for('results'))
    
    try:
        # Get Spotify client
        sp = get_spotify_client()
        if not sp:
            flash('Spotify authentication error. Please try again.', 'error')
            return redirect(url_for('results'))
            
        # Check if the user has permission to modify the selected playlist
        has_permission = check_playlist_permissions(sp, playlist_id)
        if not has_permission:
            flash('You do not have permission to modify this playlist. Make sure you own the playlist or it is set as collaborative.', 'error')
            return redirect(url_for('results'))
        
        # Collect all track URIs
        all_track_uris = []
        for result in preview_results:
            track_uris = result.get('track_uris', [])
            if track_uris:
                logger.info(f"Adding {len(track_uris)} tracks for artist {result.get('name', 'Unknown')}")
                all_track_uris.extend(track_uris)
            else:
                logger.warning(f"No track URIs found for artist {result.get('name', 'Unknown')}")
        
        # Add tracks to the playlist
        if all_track_uris:
            # Validate that all track URIs are properly formatted
            valid_track_uris = [uri for uri in all_track_uris if uri and uri.startswith('spotify:track:')]
            
            if len(valid_track_uris) != len(all_track_uris):
                logger.warning(f"Filtered out {len(all_track_uris) - len(valid_track_uris)} invalid track URIs")
            
            if valid_track_uris:
                logger.info(f"Adding {len(valid_track_uris)} valid tracks to playlist")
                success = add_tracks_to_playlist(sp, playlist_id, valid_track_uris)
                if success:
                    # Get playlist name for the success message
                    playlist_name = "playlist"
                    for playlist in session.get('user_playlists', []):
                        if playlist['id'] == playlist_id:
                            playlist_name = playlist['name']
                            break
                            
                    # Remove URIs from the preview_results for display
                    playlist_results = []
                    for result in preview_results:
                        playlist_results.append({
                            'name': result['name'],
                            'tracks': result.get('tracks', [])
                        })
                        
                    session['playlist_results'] = playlist_results
                    flash(f"Added {len(valid_track_uris)} tracks from {len(playlist_results)} artists to '{playlist_name}'!", 'success')
                else:
                    flash("Error adding tracks to the playlist", 'error')
        else:
            flash("No tracks to add to the playlist", 'warning')
    except Exception as e:
        logger.error(f"Error adding tracks to playlist: {e}")
        flash(f"Error: {str(e)}", 'error')
    
    return redirect(url_for('results'))

@app.route('/clear-playlist', methods=['POST'])
def clear_playlist_route():
    """Endpoint to clear all tracks from a Spotify playlist."""
    # Check if user is authenticated with Spotify
    if not SPOTIFY_CONFIGURED:
        flash('Spotify credentials are not configured', 'error')
        return redirect(url_for('results'))
    
    if 'spotify_token_info' not in session:
        flash('Please authenticate with Spotify first', 'error')
        return redirect(url_for('results'))
    
    # Get the selected playlist ID from the form
    playlist_id = request.form.get('playlist_id')
    if not playlist_id:
        flash('Please select a playlist', 'error')
        return redirect(url_for('results'))
        
    logger.info(f"Clearing all tracks from playlist ID: {playlist_id}")
    
    try:
        # Get Spotify client
        sp = get_spotify_client()
        if not sp:
            flash('Spotify authentication error. Please try again.', 'error')
            return redirect(url_for('results'))
            
        # Check if the user has permission to modify the selected playlist
        has_permission = check_playlist_permissions(sp, playlist_id)
        if not has_permission:
            flash('You do not have permission to modify this playlist. Make sure you own the playlist or it is set as collaborative.', 'error')
            return redirect(url_for('results'))
        
        # Get playlist name for the success message
        playlist_name = "playlist"
        for playlist in session.get('user_playlists', []):
            if playlist['id'] == playlist_id:
                playlist_name = playlist['name']
                break
        
        # Clear the playlist
        success = clear_playlist(sp, playlist_id)
        if success:
            flash(f"Successfully cleared all tracks from '{playlist_name}'", 'success')
        else:
            flash(f"Error clearing tracks from '{playlist_name}'", 'error')
    except Exception as e:
        logger.error(f"Error clearing playlist: {e}")
        flash(f"Error: {str(e)}", 'error')
    
    return redirect(url_for('results'))

@app.route('/logout')
def logout():
    """Clear Spotify authentication."""
    if 'spotify_token_info' in session:
        session.pop('spotify_token_info')
    if 'spotify_auth_state' in session:
        session.pop('spotify_auth_state')
    if 'preview_results' in session:
        session.pop('preview_results')
    if 'user_playlists' in session:
        session.pop('user_playlists')
    if 'playlist_results' in session:
        session.pop('playlist_results')
    if 'artists' in session:
        session.pop('artists')
    
    flash("Logged out from Spotify successfully", 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)