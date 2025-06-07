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
        "auth_manager": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize session state
initialize_session_state()

# Configuration
class Config:
    # IMPORTANT: Update this to match your Spotify app settings
    REDIRECT_URI = "https://echomood-ydeurclvwvw8u7zvpeedjc.streamlit.app/"
    CACHE_PATH = ".spotify_cache"
    SCOPES = [
        "user-library-read",
        "playlist-modify-public", 
        "playlist-modify-private",
        "user-top-read",
        "user-read-recently-played"
    ]

def get_spotify_credentials():
    """Get Spotify credentials from Streamlit secrets or environment variables."""
    try:
        # First try Streamlit secrets
        if hasattr(st, 'secrets'):
            client_id = st.secrets.get("SPOTIFY_CLIENT_ID", None)
            client_secret = st.secrets.get("SPOTIFY_CLIENT_SECRET", None)
            
            if client_id and client_secret:
                return client_id, client_secret
        
        # Then try environment variables
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        
        if client_id and client_secret:
            return client_id, client_secret
            
        # If no credentials found, show setup instructions
        st.error("🔐 **Spotify API credentials not found!**")
        st.info("**For Streamlit Cloud deployment:**")
        st.markdown("""
        1. Go to your app settings on Streamlit Cloud
        2. Navigate to Secrets
        3. Add the following:
        ```toml
        SPOTIFY_CLIENT_ID = "your_client_id"
        SPOTIFY_CLIENT_SECRET = "your_client_secret"
        ```
        """)
        
        st.info("**For local development:**")
        st.markdown("""
        Create a `.streamlit/secrets.toml` file with:
        ```toml
        SPOTIFY_CLIENT_ID = "your_client_id"
        SPOTIFY_CLIENT_SECRET = "your_client_secret"
        ```
        """)
        st.write("Spotify Client ID:", st.secrets.get("SPOTIFY_CLIENT_ID", "Not found"))

        
        # Temporary solution - allow manual input
        with st.expander("🔧 Enter credentials manually (temporary)"):
            col1, col2 = st.columns(2)
            with col1:
                temp_id = st.text_input("Client ID", type="password")
            with col2:
                temp_secret = st.text_input("Client Secret", type="password")
            
            if temp_id and temp_secret:
                return temp_id, temp_secret
        
        st.stop()
            
    except Exception as e:
        st.error(f"Error loading credentials: {e}")
        st.stop()

def clear_spotify_cache():
    """Clear Spotify authentication cache."""
    try:
        if os.path.exists(Config.CACHE_PATH):
            os.remove(Config.CACHE_PATH)
        # Clear from session state
        if 'spotify_client' in st.session_state:
            st.session_state['spotify_client'] = None
        if 'auth_manager' in st.session_state:
            st.session_state['auth_manager'] = None
    except Exception as e:
        logger.warning(f"Could not clear cache: {e}")

def get_auth_manager():
    """Get authenticated Spotify client - REMOVED @st.cache_resource to fix widget error."""
    try:
        client_id, client_secret = get_spotify_credentials()
        
        auth_manager = SpotifyOAuth(
            client_id="50c0b9c6df1c43db8866ec8e019f4e96",
            client_secret="64f63986097447d0a9f0481e9166b7e4",
            redirect_uri=Config.REDIRECT_URI,
            scope=" ".join(Config.SCOPES),  # Fixed: Convert list to string
            open_browser=False,
            cache_path=Config.CACHE_PATH
        )

        token_info = auth_manager.get_cached_token()

        if not token_info:
            query_params = st.query_params
            if "code" in query_params:
                code = query_params["code"]
                try:
                    token_info = auth_manager.get_access_token(code)
                except Exception as e:
                    st.error(f"Authentication failed: {e}")
                    st.info("Please try the authentication process again.")
                    # Don't use st.button in cached function - just show link
                    auth_url = auth_manager.get_authorize_url()
                    st.markdown(f"[🔐 Click here to log in to Spotify]({auth_url})")
                    st.stop()
            else:
                st.markdown("### 🔐 Please log in to Spotify")
                auth_url = auth_manager.get_authorize_url()
                st.markdown(f"[🔐 Click here to log in to Spotify]({auth_url})")
                st.info("After logging in, you'll be redirected back to this app.")
                st.stop()

        return spotipy.Spotify(auth_manager=auth_manager)
    
    except Exception as e:
        st.error(f"Failed to authenticate with Spotify: {e}")
        st.write("Please check your credentials and try again.")
        st.stop()
    return st.session_state.auth_manager

def get_spotify_client():
    """Get authenticated Spotify client with improved error handling."""
    try:
        # Check if we already have a client
        if st.session_state.spotify_client is not None:
            try:
                # Test if the client is still valid
                st.session_state.spotify_client.current_user()
                return st.session_state.spotify_client
            except:
                st.session_state.spotify_client = None
        
        auth_manager = get_auth_manager()
        
        # Check URL parameters for auth code
        query_params = st.query_params
        if "code" in query_params:
            code = query_params["code"]
            try:
                # Exchange code for token
                token_info = auth_manager.get_access_token(code, as_dict=True)
                if token_info:
                    # Clear the code from URL
                    st.query_params.clear()
                    # Create client
                    st.session_state.spotify_client = spotipy.Spotify(auth_manager=auth_manager)
                    st.rerun()
            except Exception as e:
                st.error(f"Authentication failed: {e}")
                clear_spotify_cache()
                st.query_params.clear()
                if st.button("🔄 Retry Authentication"):
                    st.rerun()
                st.stop()
        
        # Check for error in URL (user denied access)
        if "error" in query_params:
            st.error("❌ Authentication was denied. Please try again.")
            st.query_params.clear()
            if st.button("🔄 Retry Authentication"):
                st.rerun()
            st.stop()
        
        # Try to get cached token
        token_info = auth_manager.get_cached_token()
        if token_info and not auth_manager.is_token_expired(token_info):
            st.session_state.spotify_client = spotipy.Spotify(auth_manager=auth_manager)
            return st.session_state.spotify_client
        
        # Need new authentication
        auth_url = auth_manager.get_authorize_url()
        
        st.markdown("### 🎵 Welcome to EchoMood!")
        st.markdown("To create personalized playlists, you need to connect your Spotify account.")
        
        # Create columns for better layout
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("#### 🔐 Connect with Spotify")
            
            # Show the auth link prominently
            st.markdown(f"""
            <div style='text-align: center; padding: 20px; background-color: #1DB954; border-radius: 10px; margin: 20px 0;'>
                <a href="{auth_url}" target="_self" style='color: white; text-decoration: none; font-size: 18px; font-weight: bold;'>
                    🎵 Connect Spotify Account
                </a>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("**Note:** You'll be redirected to Spotify to log in, then back to this app.")
        
        # Alternative method
        with st.expander("🔧 Alternative: Manual Authentication"):
            st.markdown("If the button doesn't work, you can manually authenticate:")
            st.markdown("1. Copy this URL and paste it in a new browser tab:")
            st.code(auth_url, language="text")
            
            st.markdown("2. After authorizing, you'll be redirected. Copy the entire URL from your browser.")
            
            redirect_url = st.text_input(
                "3. Paste the redirect URL here:",
                placeholder="https://echomood-ydeurclvwvw8u7zvpeedjc.streamlit.app/?code=..."
            )
            
            if redirect_url and "code=" in redirect_url:
                try:
                    # Extract code from URL
                    parsed = urllib.parse.urlparse(redirect_url)
                    code = urllib.parse.parse_qs(parsed.query).get('code', [None])[0]
                    
                    if code:
                        token_info = auth_manager.get_access_token(code, as_dict=True)
                        if token_info:
                            st.session_state.spotify_client = spotipy.Spotify(auth_manager=auth_manager)
                            st.success("✅ Authentication successful!")
                            time.sleep(1)
                            st.rerun()
                except Exception as e:
                    st.error(f"Failed to authenticate: {e}")
        
        # Help section
        with st.expander("❓ Having trouble?"):
            st.markdown("""
            **Common issues:**
            - Make sure you're using the correct Spotify account
            - Check that pop-ups are not blocked
            - Try clearing your browser cache
            - Ensure your Spotify app redirect URI is set to:
              ```
              https://echomood-ydeurclvwvw8u7zvpeedjc.streamlit.app/
              ```
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear Cache"):
                    clear_spotify_cache()
                    st.rerun()
            with col2:
                if st.button("🔄 Refresh Page"):
                    st.rerun()
        
        st.stop()
        
    except Exception as e:
        st.error(f"❌ Authentication Error: {e}")
        if st.button("🔄 Retry"):
            clear_spotify_cache()
            st.rerun()
        st.stop()

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
        
        # Success message with user info
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✅ Connected as: **{user_info['display_name']}**")
        with col2:
            if st.button("🚪 Logout", key="logout_main"):
                clear_spotify_cache()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.query_params.clear()
                st.rerun()
    except:
        # This will trigger the authentication flow in get_spotify_client()
        return
    
    # Music source selection
    st.markdown("### 📀 Select Music Source")
    
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

    # Styled fetch button
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button('🚀 Fetch My Music', type="primary", use_container_width=True):
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

    # Apply button
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✨ Apply Mood Settings", type="primary", use_container_width=True):
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
                    if track.get('familiarity_score', 0) >= familiarity_threshold
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
                            track_artist_ids = [artist['id'] for artist in track['track']['artists'] if artist.get('id')]
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
                st.warning("😔 No tracks match your criteria. Try adjusting your settings.")

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
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Create Playlist", type="primary", use_container_width=True):
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
                    st.markdown(f"""
                    <div style='text-align: center; padding: 20px; background-color: #1DB954; border-radius: 10px; margin: 20px 0;'>
                        <a href="{playlist_url}" target="_blank" style='color: white; text-decoration: none; font-size: 18px; font-weight: bold;'>
                            🎵 Open '{playlist_name}' in Spotify →
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                    
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
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Create Another", use_container_width=True):
            st.session_state.page = "mood_and_genre"
            st.rerun()
    
    with col2:
        if st.button("📱 Different Music", use_container_width=True):
            st.session_state.page = "fetch_music"
            # Clear previous data
            st.session_state.music_data = []
            st.session_state.spotify_genres = []
            st.session_state.filtered_music_data = []
            st.rerun()
    
    with col3:
        if st.button("🏠 Start Over", use_container_width=True):
            # Clear all session state except auth
            keys_to_keep = ['spotify_client', 'auth_manager']
            for key in list(st.session_state.keys()):
                if key not in keys_to_keep:
                    del st.session_state[key]
            initialize_session_state()
            st.rerun()

# Custom CSS with improved button styling
st.markdown("""
    <style>
    /* Main app styling */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #1DB954;
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #1ed760;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
    
    /* Primary button styling */
    .stButton > button[kind="primary"] {
        background-color: #1DB954;
        font-size: 1.1rem;
        padding: 0.75rem 1.5rem;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #1ed760;
    }
    
    /* Headers and text */
    h1, h2, h3 {
        color: white;
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background-color: #1DB954;
    }
    
    /* Success/Info/Error messages */
    .stSuccess, .stInfo, .stError {
        border-radius: 10px;
    }
    
    /* Radio buttons and sliders */
    .stRadio > label {
        color: white;
    }
    
    .stSlider > label {
        color: white;
    }
    
    /* Text input */
    .stTextInput > label {
        color: white;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        color: white;
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
    st.markdown(
        "<div style='text-align: center; color: white;'>"
        "<b>EchoMood</b> • Made with ❤️ and Streamlit • Powered by Spotify"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()