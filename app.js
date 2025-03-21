// Spotify API configuration
const SPOTIFY_CLIENT_ID = 'd2776941818f424b9153f1ef3844d13c'; // Replace with your Spotify Client ID
const SPOTIFY_REDIRECT_URI = window.location.origin + '/callback';
const SPOTIFY_SCOPES = 'playlist-modify-public playlist-modify-private user-library-read';

// Global state
let spotifyToken = null;
let foundArtists = [];
let previewResults = [];
let userPlaylists = [];
// CORS proxy options
// Option 1: Public proxy (requires temporary access, visit https://cors-anywhere.herokuapp.com/corsdemo first)
let corsBypassProxy = 'https://cors-anywhere.herokuapp.com/';

// Option 2: Local proxy (requires running cors-proxy.js)
// let corsBypassProxy = 'http://localhost:8081/?url=';

// DOM Elements
const alertContainer = document.getElementById('alertContainer');
const spotifyAuthSection = document.getElementById('spotifyAuthSection');
const venueForm = document.getElementById('venueForm');
const resultsContainer = document.getElementById('resultsContainer');
const artistsList = document.getElementById('artistsList');
const previewContainer = document.getElementById('previewContainer');
const previewList = document.getElementById('previewList');
const playlistSelect = document.getElementById('playlistSelect');
const newPlaylistSection = document.getElementById('newPlaylistSection');
const newPlaylistName = document.getElementById('newPlaylistName');
const playlistForm = document.getElementById('playlistForm');
const startOverBtn = document.getElementById('startOverBtn');
const clearPlaylistBtn = document.getElementById('clearPlaylistBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const loadingMessage = document.getElementById('loadingMessage');

// Initialize the application
document.addEventListener('DOMContentLoaded', init);

function init() {
    // Check for Spotify authentication callback
    checkSpotifyCallback();
    
    // Update UI based on authentication status
    updateAuthUI();
    
    // Setup event listeners
    venueForm.addEventListener('submit', handleVenueFormSubmit);
    playlistForm.addEventListener('submit', handlePlaylistFormSubmit);
    startOverBtn.addEventListener('click', startOver);
    clearPlaylistBtn.addEventListener('click', handleClearPlaylist);
    
    // Setup playlist select behavior
    playlistSelect.addEventListener('change', function() {
        if (playlistSelect.value === 'new') {
            newPlaylistSection.style.display = 'block';
        } else {
            newPlaylistSection.style.display = 'none';
        }
        // Update clear button state when selection changes
        updateClearButtonState();
    });
}

// Authentication functions
function checkSpotifyCallback() {
    const hash = window.location.hash.substring(1);
    if (!hash) return;
    
    const params = new URLSearchParams(hash);
    const accessToken = params.get('access_token');
    const expiresIn = params.get('expires_in');
    
    if (accessToken) {
        // Clear hash from URL without reloading
        history.replaceState(null, null, ' ');
        
        // Store token with expiration
        saveToken(accessToken, expiresIn);
        
        // Fetch user playlists after successful authentication
        fetchUserPlaylists();
        
        // Show success message
        showAlert('Successfully connected to Spotify!', 'success');
    }
}

function updateAuthUI() {
    if (isAuthenticated()) {
        // User is authenticated with Spotify
        spotifyAuthSection.innerHTML = `
            <div class="spotify-status spotify-connected text-center mb-4">
                <h5>Connected to Spotify</h5>
                <p class="mb-0">Your Spotify account is connected and ready to use.</p>
                <button class="btn btn-sm btn-outline-secondary mt-2" id="logoutBtn">Disconnect</button>
            </div>
        `;
        document.getElementById('logoutBtn').addEventListener('click', logout);
        
        // Enable the form
        enableForm();
        
        // Fetch playlists if we haven't already
        if (userPlaylists.length === 0) {
            fetchUserPlaylists();
        }
    } else {
        // User needs to authenticate with Spotify
        const authUrl = getSpotifyAuthUrl();
        spotifyAuthSection.innerHTML = `
            <div class="spotify-status spotify-connect text-center mb-4">
                <h5>Connect to Spotify</h5>
                <p>Connect your Spotify account to start using this application.</p>
                <a href="${authUrl}" class="btn btn-success btn-lg" id="connectBtn">Connect Spotify</a>
            </div>
        `;
        document.getElementById('connectBtn').addEventListener('click', function() {
            showLoading('Connecting to Spotify...');
        });
        
        // Disable the form
        disableForm();
    }
}

function getSpotifyAuthUrl() {
    // Generate a random state for CSRF protection
    const state = generateRandomString(16);
    localStorage.setItem('spotify_auth_state', state);
    
    const authUrl = new URL('https://accounts.spotify.com/authorize');
    const params = {
        client_id: SPOTIFY_CLIENT_ID,
        response_type: 'token',
        redirect_uri: SPOTIFY_REDIRECT_URI,
        state: state,
        scope: SPOTIFY_SCOPES
    };
    
    // Add parameters to URL
    Object.keys(params).forEach(key => {
        authUrl.searchParams.append(key, params[key]);
    });
    
    return authUrl.toString();
}

function generateRandomString(length) {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    
    for (let i = 0; i < length; i++) {
        const randomIndex = Math.floor(Math.random() * characters.length);
        result += characters.charAt(randomIndex);
    }
    
    return result;
}

function saveToken(token, expiresIn) {
    const now = new Date();
    const expiryTime = now.getTime() + (parseInt(expiresIn) * 1000);
    
    localStorage.setItem('spotify_token', token);
    localStorage.setItem('spotify_token_expires', expiryTime);
    
    spotifyToken = token;
}

function getToken() {
    if (spotifyToken) return spotifyToken;
    
    const token = localStorage.getItem('spotify_token');
    const expiryTime = localStorage.getItem('spotify_token_expires');
    
    if (!token || !expiryTime) return null;
    
    // Check if token is still valid
    const now = new Date().getTime();
    if (now > parseInt(expiryTime)) {
        // Token has expired
        clearToken();
        return null;
    }
    
    spotifyToken = token;
    return token;
}

function clearToken() {
    localStorage.removeItem('spotify_token');
    localStorage.removeItem('spotify_token_expires');
    spotifyToken = null;
}

function isAuthenticated() {
    return getToken() !== null;
}

function logout() {
    clearToken();
    userPlaylists = [];
    updateAuthUI();
    showAlert('Disconnected from Spotify.', 'info');
}

function enableForm() {
    const inputs = venueForm.querySelectorAll('input, button');
    inputs.forEach(input => input.removeAttribute('disabled'));
}

function disableForm() {
    const inputs = venueForm.querySelectorAll('input, button');
    inputs.forEach(input => input.setAttribute('disabled', 'disabled'));
}

// UI Helper Functions
function showAlert(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 150);
        }
    }, 5000);
}

function showLoading(message) {
    loadingMessage.textContent = message || 'Working...';
    loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
}

function startOver() {
    // Reset the UI to the initial state
    resultsContainer.style.display = 'none';
    previewContainer.style.display = 'none';
    venueForm.reset();
    artistsList.innerHTML = '';
    previewList.innerHTML = '';
    
    // Clear stored data
    foundArtists = [];
    previewResults = [];
    
    // Show the form
    venueForm.style.display = 'block';
}

// Venue scraping functions
async function handleVenueFormSubmit(event) {
    event.preventDefault();
    
    if (!isAuthenticated()) {
        showAlert('Please connect to Spotify first.', 'warning');
        return;
    }
    
    const url = document.getElementById('url').value;
    const selector = document.getElementById('selector').value;
    
    if (!url) {
        showAlert('Please enter a venue URL.', 'warning');
        return;
    }
    
    showLoading('Scraping venue website for artists...');
    
    try {
        const html = await fetchVenueWebpage(url);
        const artists = extractArtists(html, selector);
        
        if (artists.length === 0) {
            showAlert('No artists found. Please check the URL and CSS selector.', 'warning');
            hideLoading();
            return;
        }
        
        // Store the found artists
        foundArtists = artists;
        
        // Display the artists
        displayArtists(artists);
        
        // Search for the artists on Spotify
        showLoading('Searching for artists on Spotify...');
        await searchArtistsOnSpotify(artists);
        
        hideLoading();
    } catch (error) {
        console.error('Error scraping venue website:', error);
        showAlert(`Error: ${error.message}`, 'danger');
        hideLoading();
    }
}

async function fetchVenueWebpage(url) {
    try {
        // Use a CORS proxy to fetch the webpage
        const response = await fetch(`${corsBypassProxy}${url}`, {
            headers: {
                'Origin': window.location.origin
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to fetch webpage: ${response.statusText}`);
        }
        
        return await response.text();
    } catch (error) {
        console.error('Error fetching webpage:', error);
        throw new Error('Failed to access the venue website. You may need to request temporary access to the CORS proxy.');
    }
}

function extractArtists(html, selector) {
    // Create a temporary DOM element to parse the HTML
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    // Find all elements matching the selector
    const elements = doc.querySelectorAll(selector);
    
    // Extract artist names
    const artistsSet = new Set();
    elements.forEach(element => {
        const artistName = element.textContent.trim();
        if (artistName) {
            artistsSet.add(artistName);
        }
    });
    
    // Convert to array and sort
    return Array.from(artistsSet).sort();
}

function displayArtists(artists) {
    // Show the results container
    resultsContainer.style.display = 'block';
    
    // Clear the list
    artistsList.innerHTML = '';
    
    // Add each artist to the list
    artists.forEach(artist => {
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item';
        listItem.textContent = artist;
        artistsList.appendChild(listItem);
    });
}

// Spotify API functions
async function fetchUserPlaylists() {
    const token = getToken();
    if (!token) return;
    
    showLoading('Fetching your Spotify playlists...');
    
    try {
        const response = await fetch('https://api.spotify.com/v1/me/playlists?limit=50', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                // Token expired or invalid
                clearToken();
                updateAuthUI();
                throw new Error('Spotify authentication expired. Please reconnect.');
            }
            throw new Error(`Failed to fetch playlists: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Filter to only include playlists the user can modify
        const currentUser = await getCurrentUser();
        userPlaylists = data.items.filter(playlist => 
            playlist.owner.id === currentUser.id || playlist.collaborative
        );
        
        // Update the playlist select dropdown
        updatePlaylistSelect();
        
        hideLoading();
    } catch (error) {
        console.error('Error fetching playlists:', error);
        showAlert(`Error: ${error.message}`, 'danger');
        hideLoading();
    }
}

async function getCurrentUser() {
    const token = getToken();
    if (!token) return null;
    
    try {
        const response = await fetch('https://api.spotify.com/v1/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to fetch user profile: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching user profile:', error);
        throw error;
    }
}

function updatePlaylistSelect() {
    // Clear existing options
    playlistSelect.innerHTML = '';
    
    // Add "Create new playlist" option
    const newOption = document.createElement('option');
    newOption.value = 'new';
    newOption.textContent = '-- Create New Playlist --';
    playlistSelect.appendChild(newOption);
    
    // Add existing playlists
    userPlaylists.forEach(playlist => {
        const option = document.createElement('option');
        option.value = playlist.id;
        option.textContent = `${playlist.name} (${playlist.tracks.total} tracks)`;
        playlistSelect.appendChild(option);
    });
    
    // Default to "Create new playlist"
    playlistSelect.value = 'new';
    newPlaylistSection.style.display = 'block';
    
    // Update the clear button state
    updateClearButtonState();
}

// Function to update the clear button state
function updateClearButtonState() {
    const clearButton = document.getElementById('clearPlaylistBtn');
    if (clearButton) {
        const selectedValue = playlistSelect.value;
        clearButton.disabled = selectedValue === 'new' || selectedValue === '';
    }
}

async function searchArtistsOnSpotify(artists) {
    const token = getToken();
    if (!token) {
        showAlert("You need to connect to Spotify first.", "warning");
        hideLoading();
        return;
    }
    
    previewResults = [];
    let processedCount = 0;
    let foundCount = 0;
    
    // Add a small delay between requests to avoid rate limiting
    const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
    
    for (const artist of artists) {
        try {
            processedCount++;
            
            // Update loading message every few artists
            if (processedCount % 5 === 0) {
                showLoading(`Processed ${processedCount}/${artists.length} artists...`);
            }
            
            // Add a small delay between requests
            await delay(10);
            
            // Search for the artist
            const artistId = await searchArtist(artist);
            if (!artistId) continue;
            
            // Get the artist's top tracks
            const tracks = await getTopTracks(artistId);
            if (tracks.length === 0) continue;
            
            // Add to preview results
            previewResults.push({
                name: artist,
                tracks: tracks.map(track => `${track.name} (${track.album.name})`),
                trackUris: tracks.map(track => track.uri)
            });
            
            foundCount++;
            
        } catch (error) {
            console.error(`Error processing artist "${artist}":`, error);
        }
    }
    
    console.log(`Processed ${artists.length} artists, found ${foundCount} with tracks`);
    
    // Display preview results
    displayPreviewResults();
}

async function searchArtist(artistName) {
    const token = getToken();
    
    if (!token) {
        console.error("No valid token found");
        showAlert("Spotify authentication expired. Please reconnect.", "error");
        return null;
    }
    
    try {
        console.log(`Searching for artist: ${artistName}`);
        const response = await fetch(`https://api.spotify.com/v1/search?q=artist:${encodeURIComponent(artistName)}&type=artist&limit=1`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        // If token expired, try to refresh the UI
        if (response.status === 401) {
            console.error("Token expired or invalid");
            clearToken();
            updateAuthUI();
            showAlert("Spotify authentication expired. Please reconnect.", "error");
            return null;
        }
        
        if (!response.ok) {
            // Log more detailed error information
            const errorText = await response.text();
            console.error(`Spotify API error (${response.status}): ${errorText}`);
            throw new Error(`Spotify API error (${response.status}): ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.artists.items.length > 0) {
            console.log(`Found artist: ${data.artists.items[0].name} (ID: ${data.artists.items[0].id})`);
            return data.artists.items[0].id;
        } else {
            console.log(`No artist found for: ${artistName}`);
            return null;
        }
    } catch (error) {
        console.error(`Error searching for artist "${artistName}":`, error);
        return null;
    }
}

async function getTopTracks(artistId) {
    const token = getToken();
    
    if (!token) {
        return [];
    }
    
    try {
        // Get the user's market if available
        let market = 'US'; // Default to US
        try {
            const user = await getCurrentUser();
            if (user && user.country) {
                market = user.country;
            }
        } catch (e) {
            console.warn('Could not determine user market, using US as default');
        }
        
        console.log(`Fetching top tracks for artist ID: ${artistId}`);
        const response = await fetch(`https://api.spotify.com/v1/artists/${artistId}/top-tracks?market=${market}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.status === 401) {
            console.error("Token expired or invalid");
            clearToken();
            updateAuthUI();
            throw new Error("Authentication expired");
        }
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Spotify API error (${response.status}): ${errorText}`);
            throw new Error(`Spotify API error: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Log the number of tracks found
        console.log(`Found ${data.tracks.length} tracks for artist ID ${artistId}`);
        
        // Return the top 2 tracks
        return data.tracks.slice(0, 2);
    } catch (error) {
        console.error(`Error getting top tracks for artist ID "${artistId}":`, error);
        return [];
    }
}

function displayPreviewResults() {
    if (previewResults.length === 0) {
        showAlert('No tracks found for the artists. Try a different venue or CSS selector.', 'warning');
        return;
    }
    
    // Show the preview container
    previewContainer.style.display = 'block';
    
    // Clear the list
    previewList.innerHTML = '';
    
    // Count total tracks
    let totalTracks = 0;
    
    // Add each artist and their tracks to the list
    previewResults.forEach(result => {
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item';
        
        // Artist name
        const artistName = document.createElement('strong');
        artistName.textContent = result.name;
        listItem.appendChild(artistName);
        
        // Tracks
        result.tracks.forEach(track => {
            const trackItem = document.createElement('div');
            trackItem.className = 'track-item';
            trackItem.textContent = track;
            listItem.appendChild(trackItem);
            totalTracks++;
        });
        
        previewList.appendChild(listItem);
    });
    
    // Update the add to playlist button
    const addToPlaylistBtn = document.getElementById('addToPlaylistBtn');
    addToPlaylistBtn.textContent = `Add ${totalTracks} Tracks to Playlist`;
}

async function handlePlaylistFormSubmit(event) {
    event.preventDefault();
    
    if (!isAuthenticated()) {
        showAlert('Please connect to Spotify first.', 'warning');
        return;
    }
    
    let playlistId = playlistSelect.value;
    
    showLoading('Working with Spotify...');
    
    try {
        // Create a new playlist if needed
        if (playlistId === 'new') {
            const name = newPlaylistName.value || 'Upcoming Shows Playlist';
            playlistId = await createPlaylist(name);
            
            if (!playlistId) {
                throw new Error('Failed to create playlist');
            }
        }
        
        // Collect all track URIs
        const allTrackUris = [];
        previewResults.forEach(result => {
            if (result.trackUris && result.trackUris.length > 0) {
                allTrackUris.push(...result.trackUris);
            }
        });
        
        if (allTrackUris.length === 0) {
            throw new Error('No tracks to add to playlist');
        }
        
        // Add tracks to the playlist
        const success = await addTracksToPlaylist(playlistId, allTrackUris);
        
        if (success) {
            showAlert(`Successfully added ${allTrackUris.length} tracks to the playlist!`, 'success');
        } else {
            throw new Error('Failed to add tracks to playlist');
        }
        
        hideLoading();
    } catch (error) {
        console.error('Error handling playlist form:', error);
        showAlert(`Error: ${error.message}`, 'danger');
        hideLoading();
    }
}

async function createPlaylist(name) {
    const token = getToken();
    if (!token) return null;
    
    try {
        // Get the current user's ID
        const user = await getCurrentUser();
        if (!user || !user.id) {
            throw new Error('Could not determine user ID');
        }
        
        // Create the playlist
        const response = await fetch(`https://api.spotify.com/v1/users/${user.id}/playlists`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                description: 'Created by Upcoming Playlist Generator',
                public: false
            })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to create playlist: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Add the new playlist to the userPlaylists array
        userPlaylists.push({
            id: data.id,
            name: data.name,
            tracks: { total: 0 }
        });
        
        return data.id;
    } catch (error) {
        console.error('Error creating playlist:', error);
        throw error;
    }
}

async function addTracksToPlaylist(playlistId, trackUris) {
    const token = getToken();
    if (!token) return false;
    
    try {
        // Spotify API can only handle 100 tracks at a time
        const chunkSize = 100;
        
        for (let i = 0; i < trackUris.length; i += chunkSize) {
            const chunk = trackUris.slice(i, i + chunkSize);
            
            const response = await fetch(`https://api.spotify.com/v1/playlists/${playlistId}/tracks`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    uris: chunk
                })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to add tracks: ${response.statusText}`);
            }
        }
        
        return true;
    } catch (error) {
        console.error('Error adding tracks to playlist:', error);
        throw error;
    }
}