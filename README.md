Here’s a complete `README.md` for your **EchoMood** project, based on the `echomood_app.py` file you uploaded. This document includes setup instructions, usage guidance, feature breakdown, and contribution notes:

---

````markdown
# 🎧 EchoMood

EchoMood is a mood-based playlist generator built with Streamlit and the Spotify Web API. It helps you discover and create Spotify playlists that match your current mood, musical taste, and familiarity preferences.

> “Discover music that matches your soul 🎶✨”

---

## 🚀 Features

- 🔐 **Spotify Login**: Authenticate securely using Spotify OAuth.
- 🎵 **Music Source Selection**: Choose between your *Liked Songs* or any *Spotify Playlist*.
- 🎼 **Mood & Genre Filters**: Fine-tune energy, positivity, danceability, acoustic feel, and more.
- 🔍 **Familiarity Tuning**: Decide how familiar or novel the playlist should feel.
- 📊 **Real-Time Audio Analysis**: Filters tracks using Spotify’s audio features API.
- 🎶 **Playlist Preview & Creation**: Create custom playlists with one click and open them in Spotify.
- 💡 **Interactive UI**: Built with modern Streamlit design, dynamic buttons, and progress bars.

---

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/echomood.git
cd echomood
````

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> *Make sure Python 3.8 or newer is installed.*

### 3. Spotify Developer Setup

* Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
* Create an app and note your **Client ID** and **Client Secret**.
* Set the **Redirect URI** to:

  ```
  https://echomood-ydeurclvwvw8u7zvpeedjc.streamlit.app/
  ```

### 4. Add Credentials

#### Option A: For **Streamlit Cloud**

Go to your app settings → **Secrets** and add:

```toml
SPOTIFY_CLIENT_ID = "your_client_id"
SPOTIFY_CLIENT_SECRET = "your_client_secret"
```

#### Option B: For **Local Development**

Create a `.streamlit/secrets.toml` file:

```toml
SPOTIFY_CLIENT_ID = "your_client_id"
SPOTIFY_CLIENT_SECRET = "your_client_secret"
```

---

## 🧠 How It Works

1. **Login** to Spotify
2. **Fetch tracks** from Liked Songs or a Playlist
3. **Analyze genres and familiarity** scores using:

   * Recent and top plays
   * Artist genre metadata
4. **Filter tracks** by:

   * Mood (valence, energy, danceability, etc.)
   * Familiarity (recent/top play weighting)
   * Genres
5. **Display filtered tracks**, preview 5 samples
6. **Generate playlist** in your account

---

## 🎨 UI Customizations

* Gradient background and green accent colors
* Styled buttons and progress bars
* Custom headers, labels, sliders, and success banners

---

## 💡 Example Usage

```bash
streamlit run echomood_app.py
```

---

## 📦 Dependencies

* `streamlit`
* `spotipy`
* `requests`
* `datetime`
* `logging`
* `random`
* `os`, `time`, `urllib`, `collections`

---

## 🤝 Contributing

Pull requests are welcome! Ideas for new features include:

* User mood presets (Happy, Sad, Workout, Chill)
* Support for album or artist search
* Save and share mood profiles

---

## 📝 License

MIT License. See `LICENSE` for more details.

---

## 🧑‍💻 Created By

**Pierce** – Developer, musician, and student from Stockton-on-Tees
🎓 GCSE 2025 | 🎶 Pianist, Clarinetist, Violist | 🎮 Tech + Music Innovator

---

> “EchoMood is where your emotions meet your music. Let your playlist speak for you.”

```

---

Let me know if you want this turned into a downloadable file or want help publishing the app to Streamlit Cloud or GitHub!
```
