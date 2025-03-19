#!/usr/bin/env python3
import argparse
import logging
from scraper import get_upcoming_artists
from spotify_integration import SpotifyHandler

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Main function to scrape upcoming artists from a venue's website
    and add their top tracks to a Spotify playlist.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Create Spotify playlists from venue schedules")
    parser.add_argument("--url", required=True, help="URL of the venue's schedule page")
    parser.add_argument("--selector", default="div.wPBHIIJzw9ltGDuXqcAD", 
                        help="CSS selector to find artist names (default: div.wPBHIIJzw9ltGDuXqcAD)")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Don't actually add tracks to playlist, just print what would be added")
    
    args = parser.parse_args()
    
    # Step 1: Scrape artists from the venue's website
    logger.info(f"Scraping artists from {args.url}")
    artists = get_upcoming_artists(args.url, args.selector)
    
    if not artists:
        logger.error("No artists found. Please check the URL and CSS selector.")
        return
    
    logger.info(f"Found {len(artists)} unique artists:")
    for artist in artists:
        logger.info(f"- {artist}")
    
    # Step 2: Process artists with Spotify
    try:
        spotify = SpotifyHandler()
        
        if args.dry_run:
            logger.info("DRY RUN MODE: Would process these artists with Spotify")
            for artist in artists:
                logger.info(f"- Would search for {artist} and add top 2 tracks")
        else:
            logger.info("Processing artists with Spotify")
            results = spotify.process_artists(artists)
            
            if results:
                logger.info(f"Added tracks from {len(results)} artists to playlist:")
                for artist in results:
                    logger.info(f"- {artist['name']}: {', '.join(artist['tracks'])}")
            else:
                logger.warning("No tracks were added to the playlist")
                
    except Exception as e:
        logger.error(f"Error processing artists with Spotify: {e}")

if __name__ == "__main__":
    main()