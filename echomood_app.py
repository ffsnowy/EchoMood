import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random

# Spotify Authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="50c0b9c6df1c43db8866ec8e019f4e96",
    client_secret="64f63986097447d0a9f0481e9166b7e4",
    redirect_uri="http://127.0.0.1:5000/callback", 
    scope=["user-library-read", "playlist-modify-public", "playlist-modify-private"]
))

# Custom CSS Styles
st.markdown("""
    <style>
    .main { 
        background-color: #121212; 
        color: white; 
    }
    h1, h2, h4, p { 
        font-family: 'Helvetica', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# Function to fetch familiarity score based on listening history
def calculate_familiarity(track):
    # Placeholder data for demonstration (you'd replace this with real listening data)
    listens_24h = random.randint(0, 10)
    listens_7d = random.randint(0, 30)
    listens_30d = random.randint(0, 50)
    listens_90d = random.randint(0, 100)

    # Assign weights to the time periods
    weight_24h = 4
    weight_7d = 3
    weight_30d = 2
    weight_90d = 1

    # Calculate familiarity score
    familiarity_score = (weight_24h * listens_24h + weight_7d * listens_7d +
                         weight_30d * listens_30d + weight_90d * listens_90d)
    familiarity_score = min(familiarity_score, 100)  # Cap the score at 100

    return familiarity_score

# Function to fetch music data from Spotify (Similar to previous)
def get_spotify_data(fetch_type, playlist_url=None):
    results = []
    offset = 0

    if fetch_type == "Liked Songs":
        while True:
            response = sp.current_user_saved_tracks(limit=50, offset=offset)
            results.extend(response['items'])
            if len(response['items']) < 50:
                break
            offset += 50
    elif fetch_type == "Playlist" and playlist_url is not None:
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
        while True:
            response = sp.playlist_tracks(playlist_id, limit=100, offset=offset)
            results.extend(response['items'])
            if len(response['items']) < 100:
                break
            offset += 100

    return results

# Main Title and Subtitle
st.title("🎧 EchoMood")
st.subheader("Discover the rhythm of your soul with EchoMood 🎶")

# Initial state settings
if "page" not in st.session_state:
    st.session_state.page = "fetch_music"

# Fetch music data (Liked Songs or Playlist)
if st.session_state.page == "fetch_music":
    fetch_choice = st.radio(
        "What do you want to fetch?",
        ("Liked Songs", "Specific Playlist"),
        index=0,
    )

    playlist_url = None
    if fetch_choice == "Specific Playlist":
        playlist_url = st.text_input("Enter the Spotify Playlist URL:")

    if st.button('Fetch Music'):
        with st.spinner('Fetching your music... please wait! 🎶'):
            if fetch_choice == "Liked Songs":
                data = get_spotify_data("Liked Songs")
            elif fetch_choice == "Specific Playlist" and playlist_url:
                data = get_spotify_data("Playlist", playlist_url)
            else:
                st.error("Please enter a valid playlist URL.")
                data = []

            # Add familiarity score to each track
            for track in data:
                track['familiarity_score'] = calculate_familiarity(track)

            st.session_state['music_data'] = data
            st.session_state.page = 'mood_and_genre'  # Move to next page
            st.rerun()

    # Display message to guide user
    st.warning("Please select your music source and click 'Fetch Music'.")

# Genre and Mood Selection (with Familiarity slider)
if st.session_state.page == "mood_and_genre":
    # Display fetched music data
    data = st.session_state.get('music_data', [])
    if not data:
        st.warning("No music fetched yet — please hit 'Fetch Music' above.")
    else:
        # Genre Selection
        st.header("🎼 Choose Genres for Your Mood")
        spotify_genres = [
            "acoustic", "afrobeat", "alt-rock", "alternative", "ambient", "black-metal", 
            "bluegrass", "blues", "bossanova", "brazil", "breakbeat", "british", "cantopop", 
            "chicago-house", "children", "chill", "classical", "club", "comedy", "country", 
            "dance", "dancehall", "death-metal", "deep-house", "detroit-techno", "disco", 
            "disney", "drum-and-bass", "dub", "dubstep", "edm", "electro", "electronic", 
            "emo", "folk", "forro", "french", "funk", "garage", "german", "gospel", "goth", 
            "grindcore", "groove", "grunge", "guitar", "happy", "hard-rock", "hardcore", 
            "hardstyle", "heavy-metal", "hip-hop", "holidays", "honky-tonk", "house", "idm", 
            "indian", "indie", "indie-pop", "industrial", "iranian", "j-dance", "j-idol", 
            "j-pop", "j-rock", "jazz", "k-pop", "kids", "latin", "latino", "malay", "mandopop", 
            "metal", "metalcore", "minimal-techno", "movies", "mpb", "new-age", "new-release", 
            "opera", "pagode", "party", "philippines-opm", "piano", "pop", "pop-film", "post-dubstep", 
            "power-pop", "progressive-house", "psych-rock", "punk", "punk-rock", "r-n-b", "rainy-day", 
            "reggae", "reggaeton", "road-trip", "rock", "rock-n-roll", "rockabilly", "romance", 
            "sad", "salsa", "samba", "sertanejo", "show-tunes", "singer-songwriter", "ska", 
            "sleep", "songwriter", "soul", "soundtracks", "spanish", "study", "summer", 
            "swedish", "synth-pop", "tango", "techno", "trance", "trip-hop", "turkish", 
            "work-out", "world-music"
            ]
        
        selected_genres = st.multiselect(
            "Pick the genres you're in the mood for:",
            spotify_genres,
            default=["chill", "pop", "indie"]  # Default genres
        )

        st.info(f"You've selected: {', '.join(selected_genres)}")

        # Mood Sliders
        st.header("🧠 Refine Your Mood")
        col1, col2, col3 = st.columns(3)

        with col1:
            valence = st.slider("Happiness (Valence)", 0.0, 1.0, 0.5, step=0.01)
            energy = st.slider("Energy", 0.0, 1.0, 0.5, step=0.01)

        with col2:
            danceability = st.slider("Danceability", 0.0, 1.0, 0.5, step=0.01)
            acousticness = st.slider("Acousticness", 0.0, 1.0, 0.5, step=0.01)

        with col3:
            instrumentalness = st.slider("Instrumentalness", 0.0, 1.0, 0.0, step=0.01)
            liveness = st.slider("Liveness", 0.0, 1.0, 0.2, step=0.01)

        # Familiarity Slider
        familiarity = st.slider("How familiar do you want your music to be?", 0, 100, 50)

        if st.button("Confirm Mood and Genre"):
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

            # Filter music based on familiarity score
            familiarity_threshold = (familiarity / 100) * 100  # Convert slider to a percentage
            filtered_data = [track for track in data if track['familiarity_score'] >= familiarity_threshold]

            # Optionally, you can add more filtering logic here to match other moods and genres as well.

            st.session_state.filtered_music_data = filtered_data
            st.session_state.page = "playlist_details"
            st.rerun()

# Playlist Details and Playlist Generation
if st.session_state.page == "playlist_details":
    st.header("🎶 Playlist Details")

    playlist_name = st.text_input("Enter the name of your playlist:")
    num_songs = st.slider("Number of songs", 1, 50, 20)

    if st.button("Generate Playlist"):
        # Create a playlist
        if playlist_name:
            user_id = sp.current_user()['id']
            new_playlist = sp.user_playlist_create(user_id, playlist_name, public=False)  # Create the playlist on Spotify
            playlist_id = new_playlist['id']

            # Get the filtered tracks (based on familiarity)
            track_ids = [track['track']['id'] for track in st.session_state.filtered_music_data[:num_songs]]

            # Add the tracks to the new playlist
            sp.playlist_add_items(playlist_id, track_ids)

            # Update session state with playlist name and number of songs
            st.session_state.page = "playlist_created"
            st.session_state.playlist_name = playlist_name
            st.session_state.num_songs = num_songs

            # Show confirmation message
            st.success(f"🎉 Your playlist '{playlist_name}' has been created and saved to your Spotify account!")

            st.rerun()

# Playlist Created Confirmation
if st.session_state.page == "playlist_created":
    st.success(f"🎶 Your playlist '{st.session_state.playlist_name}' has been successfully saved!")
    st.button("Go Back to Start")
    st.session_state.page = "fetch_music"
    st.rerun()


# ---------------------------------------------------
# Please don't delete this: Useful Terminal Commands
# cd Documents\EchoMood
# .\venv\Scripts\Activate
# streamlit run echomood_app.py
