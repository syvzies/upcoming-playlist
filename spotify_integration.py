#!/usr/bin/env python3
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SpotifyHandler:
    def __init__(self):
        """Initialize Spotify API client with proper authentication."""
        self.client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        self.client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
        self.playlist_id = os.environ.get('SPOTIFY_PLAYLIST_ID')
        
        if not all([self.client_id, self.client_secret, self.playlist_id]):
            logger.error("Missing required Spotify credentials. Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_PLAYLIST_ID environment variables.")
            raise ValueError("Missing Spotify credentials")
        
        # Set up authentication with necessary permissions
        scope = "playlist-modify-public playlist-modify-private user-library-read"
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=scope
        ))
        logger.info("Spotify client initialized successfully")
    
    def search_artist(self, artist_name):
        """Search for an artist on Spotify and return their ID."""
        try:
            logger.info(f"Searching for artist: {artist_name}")
            results = self.sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
            
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
    
    def get_top_tracks(self, artist_id, limit=2):
        """Get the top tracks for an artist."""
        try:
            logger.info(f"Fetching top {limit} tracks for artist ID: {artist_id}")
            results = self.sp.artist_top_tracks(artist_id)
            
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
    
    def add_tracks_to_playlist(self, track_uris):
        """Add tracks to the configured playlist."""
        if not track_uris:
            logger.warning("No tracks to add to playlist")
            return False
        
        try:
            logger.info(f"Adding {len(track_uris)} tracks to playlist ID: {self.playlist_id}")
            self.sp.playlist_add_items(self.playlist_id, track_uris)
            logger.info("Successfully added tracks to playlist")
            return True
        except Exception as e:
            logger.error(f"Error adding tracks to playlist: {e}")
            return False
    
    def process_artists(self, artists):
        """Process a list of artists, find their top tracks, and add to playlist."""
        added_track_count = 0
        added_artists = []
        
        for artist_name in artists:
            artist_id = self.search_artist(artist_name)
            if not artist_id:
                continue
                
            top_tracks = self.get_top_tracks(artist_id)
            if not top_tracks:
                continue
                
            track_uris = [track['uri'] for track in top_tracks]
            if self.add_tracks_to_playlist(track_uris):
                added_track_count += len(track_uris)
                added_artists.append({
                    'name': artist_name,
                    'tracks': [f"{track['name']} ({track['album']})" for track in top_tracks]
                })
        
        logger.info(f"Added {added_track_count} tracks from {len(added_artists)} artists to the playlist")
        return added_artists

if __name__ == "__main__":
    # For testing purposes
    from scraper import get_upcoming_artists
    
    # Example usage
    target_url = "https://www.bandsintown.com/v/10000903-the-chapel"
    css_selector = "div.wPBHIIJzw9ltGDuXqcAD"
    
    artists = get_upcoming_artists(target_url, css_selector)
    
    if artists:
        logger.info(f"Found {len(artists)} artists to process")
        spotify = SpotifyHandler()
        results = spotify.process_artists(artists)
        
        if results:
            logger.info("Summary of added tracks:")
            for artist in results:
                print(f"- {artist['name']}: {', '.join(artist['tracks'])}")
        else:
            logger.warning("No tracks were added to the playlist")
    else:
        logger.warning("No artists found to process")