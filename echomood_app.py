import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import urllib.parse
import random
import requests
from collections import Counter
import time
import os
from datetime import datetime, timedelta
import logging
import base64
import hashlib
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
def initialize_session_state():
    """Initialize all session state variables with default values."""
    defaults = {
        "page": "fetch_music",
        "music_data": [],
        "spotify_genres": [],
        "selected_genres": [],
        "selected_mood": {},
        "selected_familiarity": 50,
        "filtered_music_data": [],
        "playlist_name": "",
        "spotify_client": None,
        "auth_token": None,
        "user_authenticated": False,
        "auth_state": None,
        "code_verifier": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize session state
initialize_session_state()

# Configuration
class Config:
    REDIRECT_URI = "https://echomood-ydeurclvwvw8u7zvpeedjc.streamlit.app/"
    SCOPES = [
        "user-library-read",
        "playlist-modify-public", 
        "playlist-modify-private",
        "user-top-read",
        "user-read-recently-played"
    ]

def get_spotify_credentials():
    """Get Spotify credentials from environment variables or Streamlit secrets."""
    try:
        # Hardcoded credentials (you should move these to secrets in production)
        client_id = "50c0b9c6df1c43db8866ec8e019f4e96"
        client_secret = "64f63986097447d0a9f0481e9166b7e4"
        
        # Try Streamlit secrets as backup
        if not client_id or not client_secret:
            if hasattr(st, 'secrets') and 'SPOTIFY_CLIENT_ID' in st.secrets:
                client_id = st.secrets["SPOTIFY_CLIENT_ID"]
                client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
        
        if not client_id or not client_secret:
            st.error("🔐 **Spotify API credentials not found!**")
            st.stop()
            
        return client_id, client_secret
    except Exception as e:
        st.error(f"Error loading credentials: {e}")
        st.stop()


def clear_spotify_cache():
    """Clear Spotify authentication cache."""
    try:
        if os.path.exists(Config.CACHE_PATH):
            os.remove(Config.CACHE_PATH)
        # Also clear from session state
        if 'spotify_client' in st.session_state:
            del st.session_state['spotify_client']
    except Exception as e:
        logger.warning(f"Could not clear cache: {e}")


def generate_pkce_params():
    """Generate PKCE parameters for secure OAuth flow."""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge


def create_auth_url():
    """Create Spotify authorization URL with PKCE."""
    client_id, _ = get_spotify_credentials()
    
    # Generate PKCE parameters
    code_verifier, code_challenge = generate_pkce_params()
    st.session_state.code_verifier = code_verifier
    
    # Generate state parameter for security
    state = secrets.token_urlsafe(32)
    st.session_state.auth_state = state
    
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': Config.REDIRECT_URI,
        'scope': ' '.join(Config.SCOPES),
        'code_challenge_method': 'S256',
        'code_challenge': code_challenge,
        'state': state,
        'show_dialog': 'true'
    }
    
    auth_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
    return auth_url




def exchange_code_for_token(auth_code, state):
    """Exchange authorization code for access token."""
    try:
        # Verify state parameter
        if state != st.session_state.get('auth_state'):
            raise Exception("Invalid state parameter - possible CSRF attack")
        
        client_id, client_secret = get_spotify_credentials()
        
        # Prepare token request
        token_url = "https://accounts.spotify.com/api/token"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': Config.REDIRECT_URI,
            'client_id': client_id,
            'client_secret': client_secret,
            'code_verifier': st.session_state.get('code_verifier')
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Store token data in session state
            st.session_state.auth_token = {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'expires_at': time.time() + token_data.get('expires_in', 3600),
                'scope': token_data.get('scope', ''),
                'token_type': token_data.get('token_type', 'Bearer')
            }
            
            st.session_state.user_authenticated = True
            return True
        else:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        return False



def refresh_access_token():
    """Refresh the access token using refresh token."""
    try:
        if not st.session_state.auth_token or not st.session_state.auth_token.get('refresh_token'):
            return False
        
        client_id, client_secret = get_spotify_credentials()
        
        token_url = "https://accounts.spotify.com/api/token"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': st.session_state.auth_token['refresh_token'],
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Update token data
            st.session_state.auth_token.update({
                'access_token': token_data['access_token'],
                'expires_at': time.time() + token_data.get('expires_in', 3600)
            })
            
            # Keep existing refresh token if not provided
            if 'refresh_token' in token_data:
                st.session_state.auth_token['refresh_token'] = token_data['refresh_token']
            
            return True
        else:
            logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return False




def is_token_valid():
    """Check if the current token is valid and not expired."""
    if not st.session_state.auth_token:
        return False
    
    # Check if token is expired (with 5 minute buffer)
    if time.time() >= st.session_state.auth_token.get('expires_at', 0) - 300:
        # Try to refresh the token
        if st.session_state.auth_token.get('refresh_token'):
            return refresh_access_token()
        else:
            return False
    
    return True




def get_spotify_client():
    """Get authenticated Spotify client with improved error handling."""
    try:
        # Check URL parameters for authorization code
        query_params = st.query_params
        
        if "code" in query_params and "state" in query_params:
            auth_code = query_params["code"]
            state = query_params["state"]
            
            # Clear URL parameters immediately
            st.query_params.clear()
            
            # Exchange code for token
            if exchange_code_for_token(auth_code, state):
                st.success("✅ Authentication successful!")
                st.rerun()
            else:
                st.error("❌ Authentication failed. Please try again.")
                st.session_state.user_authenticated = False
                st.rerun()
        
        # Check if we have a valid token
        if not is_token_valid():
            st.session_state.user_authenticated = False
            return None
        
        # Create Spotify client with current token
        sp = spotipy.Spotify(auth=st.session_state.auth_token['access_token'])
        
        # Test the connection
        try:
            user_info = sp.current_user()
            st.session_state.user_authenticated = True
            return sp
        except Exception as e:
            logger.error(f"Spotify API test failed: {e}")
            st.session_state.user_authenticated = False
            st.session_state.auth_token = None
            return None
            
    except Exception as e:
        logger.error(f"Error getting Spotify client: {e}")
        st.session_state.user_authenticated = False
        return None




def clear_authentication():
    """Clear all authentication data."""
    st.session_state.auth_token = None
    st.session_state.user_authenticated = False
    st.session_state.auth_state = None
    st.session_state.code_verifier = None
    st.session_state.spotify_client = None

def render_authentication_page():
    """Render a clean authentication page."""
    st.markdown("### 🎵 Welcome to EchoMood")
    st.markdown("Connect your Spotify account to discover music that matches your mood!")
    
    # Create columns for better layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; background: rgba(255,255,255,0.1); border-radius: 15px; margin: 2rem 0;">
            <h4>🔐 Spotify Authentication Required</h4>
            <p>To create personalized playlists, we need access to your Spotify account.</p>
            <p><strong>We will only:</strong></p>
            <ul style="text-align: left; display: inline-block;">
                <li>Read your saved songs and playlists</li>
                <li>Create new playlists for you</li>
                <li>Analyze your music preferences</li>
            </ul>
            <p><em>Your privacy and data security are our top priorities.</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create authentication button
        auth_url = create_auth_url()
        
        st.markdown(f"""
        <div style="text-align: center; margin: 20px 0;">
            <a href="{auth_url}" target="_self" style="
                background: linear-gradient(45deg, #1DB954, #1ed760);
                color: white;
                padding: 15px 40px;
                text-decoration: none;
                border-radius: 30px;
                font-weight: bold;
                font-size: 18px;
                display: inline-block;
                margin: 10px;
                box-shadow: 0 6px 20px rgba(29, 185, 84, 0.4);
                transition: all 0.3s ease;
                border: none;
            " onmouseover="this.style.transform='translateY(-3px)'; this.style.boxShadow='0 8px 25px rgba(29, 185, 84, 0.6)';" 
               onmouseout="this.style.transform='translateY(0px)'; this.style.boxShadow='0 6px 20px rgba(29, 185, 84, 0.4)';">
                🎵 Connect to Spotify
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("*Click the button above to securely connect your Spotify account*")
    
    # Troubleshooting section
    with st.expander("🔧 Having Issues?"):
        st.markdown("""
        **Common solutions:**
        
        1. **Pop-up blocked?** Make sure your browser allows pop-ups for this site
        2. **Already connected?** Try refreshing the page
        3. **Still not working?** Clear your browser cache and try again
        
        If you continue having issues, the authentication should redirect you back automatically after authorization.
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Page"):
                st.rerun()
        with col2:
            if st.button("🗑️ Clear Session"):
                clear_authentication()
                st.rerun()
                



def calculate_real_familiarity_batch(track_ids, sp):
    """Calculate familiarity scores for multiple tracks efficiently."""
    try:
        # Get recently played tracks once
        recent_tracks = sp.current_user_recently_played(limit=50)
        recent_track_ids = [item['track']['id'] for item in recent_tracks['items']]
        recent_counts = Counter(recent_track_ids)
        
        # Get top tracks once
        top_track_ids = set()
        try:
            for time_range in ['short_term', 'medium_term']:
                top_tracks = sp.current_user_top_tracks(time_range=time_range, limit=50)
                top_track_ids.update(track['id'] for track in top_tracks['items'])
        except Exception:
            pass  # Continue without top tracks if it fails
        
        # Calculate scores for all tracks
        familiarity_scores = {}
        for track_id in track_ids:
            play_count = recent_counts.get(track_id, 0)
            base_score = min(play_count * 15, 60)
            top_bonus = 40 if track_id in top_track_ids else 0
            familiarity_scores[track_id] = min(base_score + top_bonus, 100)
        
        return familiarity_scores
        
    except Exception as e:
        logger.warning(f"Could not calculate familiarity batch: {e}")
        # Return random scores as fallback
        return {track_id: random.randint(0, 100) for track_id in track_ids}



def get_spotify_genres_from_tracks(tracks, sp):
    """Fetch genres from tracks' artists."""
    try:
        artist_ids = set()
        
        # Collect all unique artist IDs
        for item in tracks:
            if 'track' in item and item['track'] and 'artists' in item['track']:
                for artist in item['track']['artists']:
                    if artist.get('id'):
                        artist_ids.add(artist['id'])

        if not artist_ids:
            return []

        artist_ids = list(artist_ids)
        artist_genres = {}

        # Fetch artist information in batches of 50
        for i in range(0, len(artist_ids), 50):
            batch = artist_ids[i:i+50]
            try:
                results = sp.artists(batch)
                for artist in results['artists']:
                    if artist:
                        artist_genres[artist['id']] = artist.get('genres', [])
            except Exception as e:
                logger.warning(f"Failed to fetch artists batch {i//50 + 1}: {e}")
                continue

        # Collect all genres and count them
        all_genres = []
        for artist_id, genres in artist_genres.items():
            all_genres.extend(genres)

        # Return most common genres
        genre_counts = Counter(all_genres)
        return [genre for genre, count in genre_counts.most_common(30)]
        
    except Exception as e:
        logger.error(f"Error fetching genres: {e}")
        return []

def get_spotify_data(fetch_type, playlist_url=None, progress_bar=None):
    """Fetch music data from Spotify."""
    try:
        sp = get_spotify_client()
        if not sp:
            return []
            
        results = []
        offset = 0
        total = 0

        if fetch_type == "Liked Songs":
            try:
                # Get total count first
                initial_response = sp.current_user_saved_tracks(limit=1)
                total = initial_response['total']
                
                if total == 0:
                    st.warning("No liked songs found. Please like some songs on Spotify first!")
                    return []

                # Fetch all liked songs
                while True:
                    response = sp.current_user_saved_tracks(limit=50, offset=offset)
                    batch = response['items']
                    results.extend(batch)
                    offset += 50
                    
                    if progress_bar:
                        progress = min(int(len(results) / total * 100), 100)
                        progress_bar.progress(progress, text=f"Loading tracks... ({len(results)}/{total})")
                    
                    if len(batch) < 50:
                        break
                        
            except Exception as e:
                st.error(f"Failed to fetch liked songs: {e}")
                return []

        elif fetch_type == "Playlist" and playlist_url:
            try:
                # Extract playlist ID from URL
                if "/playlist/" in playlist_url:
                    playlist_id = playlist_url.split("/playlist/")[1].split("?")[0]
                else:
                    st.error("Invalid playlist URL format")
                    return []

                # Get playlist info
                playlist_info = sp.playlist(playlist_id)
                total = playlist_info['tracks']['total']
                
                if total == 0:
                    st.warning("This playlist is empty!")
                    return []

                # Fetch all playlist tracks
                while True:
                    response = sp.playlist_tracks(playlist_id, limit=100, offset=offset)
                    batch = response['items']
                    results.extend(batch)
                    offset += 100
                    
                    if progress_bar:
                        progress = min(int(len(results) / total * 100), 100)
                        progress_bar.progress(progress, text=f"Loading tracks... ({len(results)}/{total})")
                    
                    if len(batch) < 100:
                        break
                        
            except Exception as e:
                st.error(f"Failed to fetch playlist: {e}")
                return []

        # Filter out tracks without valid IDs
        valid_results = []
        for item in results:
            if (item.get('track') and 
                item['track'] and 
                item['track'].get('id') and 
                item['track'].get('name')):
                valid_results.append(item)

        return valid_results
        
    except Exception as e:
        st.error(f"Error fetching music data: {e}")
        return []


def filter_by_audio_features(tracks, mood_params, sp, tolerance=0.3):
    """Filter tracks based on audio features matching mood parameters."""
    try:
        if not tracks:
            return []
            
        track_ids = [t['track']['id'] for t in tracks if t.get('track', {}).get('id')]
        
        if not track_ids:
            return []

        filtered_tracks = []
        
        # Process tracks in batches of 100 (Spotify API limit)
        for i in range(0, len(track_ids), 100):
            batch_ids = track_ids[i:i+100]
            batch_tracks = tracks[i:i+100]
            
            try:
                features_list = sp.audio_features(batch_ids)
                
                for track, features in zip(batch_tracks, features_list):
                    if features and matches_mood(features, mood_params, tolerance):
                        filtered_tracks.append(track)
                        
            except Exception as e:
                logger.warning(f"Failed to get audio features for batch {i//100 + 1}: {e}")
                # If audio features fail, include tracks anyway
                filtered_tracks.extend(batch_tracks)
                
        return filtered_tracks
        
    except Exception as e:
        logger.error(f"Error filtering by audio features: {e}")
        return tracks  # Return original tracks if filtering fails

def matches_mood(features, mood_params, tolerance=0.3):
    """Check if track's audio features match the desired mood."""
    try:
        for param, target_value in mood_params.items():
            if param in features and features[param] is not None:
                if abs(features[param] - target_value) > tolerance:
                    return False
        return True
    except Exception:
        return True  # Include track if we can't determine fit

def validate_playlist_url(url):
    """Validate Spotify playlist URL."""
    if not url:
        return False, "Please enter a playlist URL"
    
    if "spotify.com/playlist/" not in url:
        return False, "Please enter a valid Spotify playlist URL (must contain 'spotify.com/playlist/')"
    
    return True, ""

def render_fetch_music_page():
    """Render the music fetching page with authentication status."""
    st.header("🎵 Choose Your Music Source")
    
    # Show authentication status
    try:
        sp = get_spotify_client()
        user_info = sp.current_user()
        st.success(f"✅ Logged in as: **{user_info['display_name']}**")
        
        # Add logout option in sidebar or small button
        with st.sidebar:
            if st.button("🚪 Logout"):
                clear_spotify_cache()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.query_params.clear()
                st.rerun()
    except:
        # This will trigger the authentication flow in get_spotify_client()
        return
    
    fetch_choice = st.radio(
        "What music would you like to analyze?",
        ("Liked Songs", "Specific Playlist"),
        help="Choose 'Liked Songs' to use your saved tracks, or 'Specific Playlist' to analyze a particular playlist"
    )

    playlist_url = None
    if fetch_choice == "Specific Playlist":
        playlist_url = st.text_input(
            "Enter the Spotify Playlist URL:",
            placeholder="https://open.spotify.com/playlist/..."
        )
        
        if playlist_url:
            is_valid, error_msg = validate_playlist_url(playlist_url)
            if not is_valid:
                st.error(error_msg)
                return

    if st.button('🚀 Fetch My Music', type="primary"):
        if fetch_choice == "Specific Playlist" and not playlist_url:
            st.error("Please enter a playlist URL first!")
            return
            
        with st.spinner('🎶 Fetching your music... This may take a moment!'):
            progress_bar = st.progress(0, text="Initializing...")
            
            # Fetch the data
            if fetch_choice == "Liked Songs":
                data = get_spotify_data("Liked Songs", progress_bar=progress_bar)
            else:
                data = get_spotify_data("Playlist", playlist_url, progress_bar=progress_bar)

            if not data:
                st.error("No music data could be fetched. Please try again.")
                return

            progress_bar.progress(80, text="Calculating familiarity scores...")
            
            sp = get_spotify_client()
            
            # Get all track IDs at once
            track_ids = [track['track']['id'] for track in data if track.get('track', {}).get('id')]
            
            # Calculate familiarity scores in batch
            familiarity_scores = calculate_real_familiarity_batch(track_ids, sp)
            
            # Assign scores to tracks
            for track in data:
                track_id = track.get('track', {}).get('id')
                if track_id:
                    track['familiarity_score'] = familiarity_scores.get(track_id, 0)

            progress_bar.progress(100, text="Complete!")
            
            # Store data and move to next page
            st.session_state.music_data = data
            st.session_state.page = 'mood_and_genre'
            
            st.success(f"✅ Successfully loaded {len(data)} tracks!")
            time.sleep(1)
            st.rerun()

def render_mood_selection_page():
    """Render the mood and genre selection page."""
    # Check authentication
    sp = get_spotify_client()
    if not sp or not st.session_state.user_authenticated:
        render_authentication_page()
        return
    
    st.header("🎼 Customize Your Mood")
    
    # Fetch genres if not already done
    if not st.session_state.spotify_genres:
        with st.spinner("🔍 Analyzing genres in your music..."):
            sp = get_spotify_client()
            st.session_state.spotify_genres = get_spotify_genres_from_tracks(
                st.session_state.music_data, sp
            )

    spotify_genres = st.session_state.spotify_genres

    if not spotify_genres:
        st.warning("⚠️ Couldn't detect genres from your music. You can still create a playlist based on mood!")
        selected_genres = []
    else:
        st.subheader("🎵 Select Genres")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_genres = st.multiselect(
                "Pick genres that match your current vibe:",
                spotify_genres,
                default=[g for g in ["pop", "rock", "indie", "electronic", "hip hop"] 
                        if g in spotify_genres][:3],
                help="Select the genres you're in the mood for right now"
            )
        
        with col2:
            if st.button("Select All"):
                selected_genres = spotify_genres
                st.rerun()

    st.subheader("🧠 Fine-tune Your Mood")
    
    # Mood sliders in a nice layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Energy & Vibe**")
        valence = st.slider("😊 Happiness/Positivity", 0.0, 1.0, 0.5, step=0.05,
                           help="0 = Sad/Dark, 1 = Happy/Uplifting")
        energy = st.slider("⚡ Energy Level", 0.0, 1.0, 0.5, step=0.05,
                          help="0 = Calm/Peaceful, 1 = Intense/Energetic")
        danceability = st.slider("💃 Danceability", 0.0, 1.0, 0.5, step=0.05,
                                help="0 = Not danceable, 1 = Very danceable")
        
    with col2:
        st.write("**Sound Character**")
        acousticness = st.slider("🎸 Acoustic Sound", 0.0, 1.0, 0.3, step=0.05,
                                help="0 = Electronic/Produced, 1 = Acoustic/Organic")
        instrumentalness = st.slider("🎼 Instrumental Focus", 0.0, 1.0, 0.1, step=0.05,
                                   help="0 = Vocal focus, 1 = Instrumental focus")
        liveness = st.slider("🎤 Live Recording Feel", 0.0, 1.0, 0.2, step=0.05,
                           help="0 = Studio recorded, 1 = Live performance")

    st.subheader("🔍 Discovery Settings")
    familiarity = st.slider(
        "How familiar should the music be?", 
        0, 100, 50,
        help="0 = Only new/unfamiliar songs, 100 = Only familiar favorites"
    )
    
    # Show selected mood summary
    with st.expander("📊 Your Mood Summary", expanded=False):
        mood_labels = {
            'valence': ('😊 Happiness', valence),
            'energy': ('⚡ Energy', energy), 
            'danceability': ('💃 Danceability', danceability),
            'acousticness': ('🎸 Acousticness', acousticness),
            'instrumentalness': ('🎼 Instrumentalness', instrumentalness),
            'liveness': ('🎤 Liveness', liveness)
        }
        
        for label, value in mood_labels.values():
            st.progress(value, text=f"{label}: {value:.2f}")

    if st.button("✨ Apply Mood Settings", type="primary"):
        # Store selections
        st.session_state.selected_genres = selected_genres
        st.session_state.selected_mood = {
            "valence": valence,
            "energy": energy,
            "danceability": danceability,
            "acousticness": acousticness,
            "instrumentalness": instrumentalness,
            "liveness": liveness
        }
        st.session_state.selected_familiarity = familiarity

        # Filter music based on selections
        with st.spinner("🎯 Filtering tracks to match your mood..."):
            sp = get_spotify_client()
            
            # Start with all tracks
            filtered_tracks = st.session_state.music_data.copy()
            
            # Filter by familiarity
            familiarity_threshold = familiarity
            filtered_tracks = [
                track for track in filtered_tracks 
                if track['familiarity_score'] >= familiarity_threshold
            ]
            
            # Filter by genres if any selected
            if selected_genres:
                genre_filtered = []
                track_genres_map = {}
                
                # Get genres for filtering
                artist_ids = set()
                for item in st.session_state.music_data:
                    if 'track' in item and item['track'] and 'artists' in item['track']:
                        for artist in item['track']['artists']:
                            if artist.get('id'):
                                artist_ids.add(artist['id'])

                # Fetch artist genres in batches
                artist_genres = {}
                artist_ids = list(artist_ids)
                
                for i in range(0, len(artist_ids), 50):
                    batch = artist_ids[i:i+50]
                    try:
                        results = sp.artists(batch)
                        for artist in results['artists']:
                            if artist:
                                artist_genres[artist['id']] = artist.get('genres', [])
                    except Exception as e:
                        logger.warning(f"Failed to fetch artist genres: {e}")
                        continue

                # Filter tracks by genre
                for track in filtered_tracks:
                    if 'track' in track and track['track'] and 'artists' in track['track']:
                        track_artist_ids = [artist['id'] for artist in track['track']['artists']]
                        track_genres = set()
                        for artist_id in track_artist_ids:
                            track_genres.update(artist_genres.get(artist_id, []))
                        
                        # Check if any selected genre matches track genres
                        if any(genre.lower() in [tg.lower() for tg in track_genres] for genre in selected_genres):
                            genre_filtered.append(track)
                
                filtered_tracks = genre_filtered if genre_filtered else filtered_tracks

            # Filter by audio features/mood
            filtered_tracks = filter_by_audio_features(
                filtered_tracks, st.session_state.selected_mood, sp
            )

            st.session_state.filtered_music_data = filtered_tracks

        if filtered_tracks:
            st.success(f"🎯 Found {len(filtered_tracks)} tracks matching your criteria!")
            st.session_state.page = "playlist_details"
            st.rerun()
        else:
            st.warning("😔 No tracks match your criteria. Try adjusting your settings and try again.")

def render_playlist_details_page():
    """Render the playlist creation page."""
    st.header("🎶 Create Your Playlist")
    
    filtered_data = st.session_state.filtered_music_data
    
    if not filtered_data:
        st.warning("No tracks found matching your criteria.")
        if st.button("← Go Back to Mood Selection"):
            st.session_state.page = "mood_and_genre"
            st.rerun()
        return

    # Playlist settings
    col1, col2 = st.columns([2, 1])
    
    with col1:
        playlist_name = st.text_input(
            "Playlist Name:",
            value=f"EchoMood - {datetime.now().strftime('%B %d')}",
            help="Give your playlist a memorable name"
        )
    
    with col2:
        num_songs = st.slider(
            "Number of Songs", 
            1, min(len(filtered_data), 50), 
            min(20, len(filtered_data)),
            help=f"Choose up to {min(len(filtered_data), 50)} songs"
        )

    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        shuffle_enabled = st.checkbox("Shuffle playlist order", value=True)
        make_public = st.checkbox("Make playlist public", value=False)

    # Preview some tracks
    st.subheader("🎵 Track Preview")
    preview_count = min(5, len(filtered_data))
    preview_tracks = random.sample(filtered_data, preview_count) if shuffle_enabled else filtered_data[:preview_count]
    
    for i, track in enumerate(preview_tracks):
        track_info = track['track']
        artists = ", ".join([artist['name'] for artist in track_info['artists']])
        familiarity = track.get('familiarity_score', 0)
        
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.write(f"**{track_info['name']}**")
        with col2:
            st.write(f"by {artists}")
        with col3:
            st.write(f"Familiarity: {familiarity}%")

    if preview_count < len(filtered_data):
        st.write(f"... and {len(filtered_data) - preview_count} more tracks")

    # Create playlist button
    if st.button("🚀 Create Playlist", type="primary"):
        if not playlist_name.strip():
            st.error("Please enter a playlist name!")
            return

        try:
            with st.spinner("🎵 Creating your playlist..."):
                sp = get_spotify_client()
                user_id = sp.current_user()['id']
                
                # Create the playlist
                new_playlist = sp.user_playlist_create(
                    user_id, 
                    playlist_name.strip(), 
                    public=make_public,
                    description=f"Created with EchoMood - A playlist matching your current vibe"
                )
                playlist_id = new_playlist['id']
                
                # Prepare track IDs
                track_ids = [
                    track['track']['id'] 
                    for track in filtered_data 
                    if track.get('track', {}).get('id')
                ]

                if shuffle_enabled:
                    random.shuffle(track_ids)

                # Limit to requested number of songs
                track_ids = track_ids[:num_songs]

                # Add tracks in batches of 100
                progress_bar = st.progress(0, text="Adding tracks to playlist...")
                
                for i in range(0, len(track_ids), 100):
                    batch = track_ids[i:i + 100]
                    sp.playlist_add_items(playlist_id, batch)
                    
                    progress = int((i + len(batch)) / len(track_ids) * 100)
                    progress_bar.progress(progress, text=f"Added {i + len(batch)}/{len(track_ids)} tracks...")

                progress_bar.progress(100, text="Playlist created successfully!")

                # Success message
                st.success(f"🎉 Playlist '{playlist_name}' created successfully!")
                st.balloons()
                
                playlist_url = new_playlist['external_urls']['spotify']
                st.markdown(f"🎵 **[Open '{playlist_name}' in Spotify →]({playlist_url})**")
                
                # Store playlist info
                st.session_state.playlist_name = playlist_name
                st.session_state.page = "playlist_created"

        except Exception as e:
            st.error(f"Failed to create playlist: {e}")
            logger.error(f"Playlist creation error: {e}")

def render_playlist_created_page():
    """Render the success page after playlist creation."""
    st.header("🎉 Playlist Created Successfully!")
    
    st.success(f"Your playlist '{st.session_state.playlist_name}' is ready to enjoy!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Create Another Playlist"):
            st.session_state.page = "mood_and_genre"
            st.rerun()
    
    with col2:
        if st.button("📱 Use Different Music"):
            st.session_state.page = "fetch_music"
            # Clear previous data
            st.session_state.music_data = []
            st.session_state.spotify_genres = []
            st.session_state.filtered_music_data = []
            st.rerun()
    
    with col3:
        if st.button("🏠 Start Over"):
            # Clear all session state
            for key in list(st.session_state.keys()):
                if key != 'spotify_client':
                    del st.session_state[key]
            initialize_session_state()
            st.rerun()

# Custom CSS
st.markdown("""
    <style>
    .main { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; 
    }
    .stApp > header {
        background-color: transparent;
    }
    .stButton > button {
        background: linear-gradient(45deg, #1DB954, #1ed760);
        color: white;
        border: none;
        border-radius: 25px;
        font-weight: bold;
    }
    .stButton > button:hover {
        background: linear-gradient(45deg, #1ed760, #1DB954);
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    h1, h2, h3, h4, p { 
        font-family: 'Helvetica', sans-serif;
    }
    .stProgress > div > div {
        background: linear-gradient(45deg, #1DB954, #1ed760);
    }
    </style>
    """, unsafe_allow_html=True)

# Main App
def main():
    # App title and subtitle
    st.title("🎧 EchoMood")
    st.subheader("Discover music that matches your soul 🎶✨")
    
    # Navigation
    pages = {
        "fetch_music": render_fetch_music_page,
        "mood_and_genre": render_mood_selection_page, 
        "playlist_details": render_playlist_details_page,
        "playlist_created": render_playlist_created_page
    }
    
    # Render current page
    current_page = st.session_state.page
    if current_page in pages:
        pages[current_page]()
    else:
        st.error("Unknown page. Redirecting...")
        st.session_state.page = "fetch_music"
        st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("**EchoMood** • Made with ❤️ and Streamlit • Powered by Spotify")

if __name__ == "__main__":
    main()
# ---------------------------------------------------
# Please don't delete this: Useful Terminal Commands
# cd Documents\EchoMood
# .\venv\Scripts\Activate
# streamlit run echomood_app.py
#client_id = "50c0b9c6df1c43db8866ec8e019f4e96"
#client_secret = "64f63986097447d0a9f0481e9166b7e4

#https://echomood-ydeurclvwvw8u7zvpeedjc.streamlit.app