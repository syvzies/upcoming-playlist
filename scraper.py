#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_webpage(url):
    """Fetch the webpage content from the specified URL."""
    try:
        logger.info(f"Fetching webpage from {url}")
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error fetching webpage: {e}")
        return None

def extract_artists(html_content, selector):
    """Extract artist names from the HTML content using the provided CSS selector."""
    try:
        logger.info("Parsing HTML content")
        soup = BeautifulSoup(html_content, 'html.parser')
        artists = set()  # Using a set to ensure uniqueness
        
        elements = soup.select(selector)
        
        logger.info(f"Found {len(elements)} potential artist entries")
        
        for element in elements:
            artist_name = element.text.strip()
            if artist_name:
                artists.add(artist_name)
        
        return sorted(list(artists))  # Convert back to sorted list for consistent output
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return []

def get_upcoming_artists(url, selector):
    """Get a list of upcoming artists from the specified webpage."""
    html_content = fetch_webpage(url)
    if html_content:
        return extract_artists(html_content, selector)
    return []

if __name__ == "__main__":
    # Example usage - update with the actual website URL and CSS selector
    target_url = "https://www.bandsintown.com/v/10000903-the-chapel"
    css_selector = "div.wPBHIIJzw9ltGDuXqcAD"  # Selector for div elements with the specified class
    
    artists = get_upcoming_artists(target_url, css_selector)
    
    if artists:
        logger.info(f"Found {len(artists)} upcoming artists:")
        for artist in artists:
            print(f"- {artist}")
    else:
        logger.warning("No artists found. Check the URL and CSS selector.")