import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Streamlit Page Config
st.set_page_config(page_title="EchoMood", page_icon="🎵", layout="wide")

# Spotify Authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="50c0b9c6df1c43db8866ec8e019f4e96",
    client_secret="64f63986097447d0a9f0481e9166b7e4",
    redirect_uri="http://127.0.0.1:5000/callback", 
    scope=["user-library-read"]
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

# Main Title and Subtitle
st.title("🎧 EchoMood")
st.subheader("Discover the rhythm of your soul with EchoMood 🎶")

# Spotify Data Fetching Function
def get_spotify_data(fetch_type, playlist_id=None):
    results = []
    offset = 0

    if fetch_type == "Liked Songs":
        while True:
            response = sp.current_user_saved_tracks(limit=50, offset=offset)
            results.extend(response['items'])
            if len(response['items']) < 50:
                break
            offset += 50

    elif fetch_type == "Playlist" and playlist_id is not None:
        playlist_id = playlist_id.split("/")[-1].split("?")[0]
        while True:
            response = sp.playlist_tracks(playlist_id, limit=100, offset=offset)
            results.extend(response['items'])
            if len(response['items']) < 100:
                break
            offset += 100

    return results

# UI for Fetching Music
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

    if data:
        st.success(f"Found {len(data)} tracks! 🎉")

        html_blocks = ""

        for track in data:
            track_name = track['track']['name']
            artist_name = track['track']['artists'][0]['name']
            track_url = track['track']['external_urls']['spotify']
            album_image = track['track']['album']['images'][0]['url'] if track['track']['album']['images'] else None

            if album_image:
                html_blocks += f"""
                <div style="display: flex; align-items: center; background-color: #181818; border-radius: 10px; padding: 10px; margin: 10px 0;">
                    <img src="{album_image}" alt="Album Art" style="width:60px; height:60px; border-radius:5px; margin-right:10px;">
                    <div>
                        <h4 style="margin:0; font-size: 18px; font-weight: bold;">{track_name}</h4>
                        <p style="margin:0; font-size: 14px;">by {artist_name}</p>
                        <a href="{track_url}" style="color: #1db954; font-size: 14px;">Listen on Spotify</a>
                    </div>
                </div>
                """

        st.markdown(html_blocks, unsafe_allow_html=True)

    else:
        st.warning("No tracks found.")

# ---------------------------------------------------
# Please don't delete this: Useful Terminal Commands
# cd Documents\EchoMood
# .\venv\Scripts\Activate
# streamlit run app.py
