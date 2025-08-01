import streamlit as st
import random
from googleapiclient.discovery import build
import requests
import os

# Load environment variables
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
HF_TOKEN = st.secrets["HF_TOKEN"]

#-------------------------

@st.cache_data(ttl=3600)  # Cache for 1 hour
def search_youtube_video(query, api_key):
    youtube = build("youtube", "v3", developerKey=api_key)
    request = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        videoCategoryId="10",  # Music category
        maxResults=5,  # Reduced from 10 to 5 for faster response
        videoEmbeddable="true",
    )
    response = request.execute()
    videos = response.get("items", [])
    if videos:
        selected_video = random.choice(videos)
        video_id = selected_video["id"]["videoId"]
        video_title = selected_video["snippet"]["title"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        return video_title, video_url 
    return None, None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_emotion_label(text):
    """Cached emotion classification to avoid repeated API calls"""
    api_url = "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}"
    }
    
    # Add timeout and retry logic
    try:
        response = requests.post(
            api_url, 
            headers=headers, 
            json={"inputs": text},
            timeout=10  # 10 second timeout
        )
        response.raise_for_status()  # Raise exception for bad status codes
        
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            top_label = result[0][0]["label"].lower()
            return top_label
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
    except Exception as e:
        st.error("Error from HuggingFace API")
        print(e)

    return "unknown"

# Initialize session state for better performance
if 'final_mood' not in st.session_state:
    st.session_state.final_mood = "unknown"
if 'video_data' not in st.session_state:
    st.session_state.video_data = None

# ----------------------
st.title("Mood Detector App 😊")

input_method = st.radio(
    "How do you want to share your mood?",
    ("Type my feeling", "Select from dropdown")
)

# Use session state to avoid recalculating
mood_changed = False

if input_method == "Type my feeling":
    user_input = st.text_input(
        "How are you feeling today? (Type your feeling)"
    )
    if user_input:
        # Only call API if input changed
        if 'last_input' not in st.session_state or st.session_state.last_input != user_input:
            with st.spinner("Analyzing your mood..."):
                results = get_emotion_label(user_input)
                if results and results != "unknown":
                    st.session_state.final_mood = results.lower()
                    mood_changed = True
                st.session_state.last_input = user_input

elif input_method == "Select from dropdown":
    mood_option = st.selectbox("Select your mood:", ["Choose...", "joy", "sadness", "anger", "surprise", "fear", "disgust", "neutral"])
    if mood_option != "Choose...":
        if st.session_state.final_mood != mood_option.lower():
            st.session_state.final_mood = mood_option.lower()
            mood_changed = True

# Emojis for moods
mood_emojis = {
    "joy": "😄",
    "sadness": "😢",
    "anger": "😡",
    "surprise": "😲",
    "fear": "😨",
    "disgust": "🤢",
    "neutral": "😐",
    "unknown": "❓"
}

st.subheader(f"Final Detected Mood: {st.session_state.final_mood.capitalize()} {mood_emojis.get(st.session_state.final_mood, '')}")

# Suggestions - using constants for better performance
SUGGESTIONS = {
    "joy": ["Enjoy your day and spread the positivity! 🌟", "Keep smiling and live life to your fullest!", "You're awesome, keep up the good work!"],
    "sadness": ["Take care! Things will get better 💛", "Sending virtual hugs, things will always get better", "You're not alone in this! Don't give up!"],
    "anger": ["Take a deep breath. You got this. 💨", "Step away and reset.", "Channel your energy positively!"],
    "fear": ["You are stronger than you think.", "Breathe. Face it one step at a time.", "Courage starts with showing up."],
    "surprise": ["Life is full of surprises!", "Embrace the unexpected!", "Wow, that was unexpected!"],
    "disgust": ["It's okay to feel that way sometimes.", "Try to focus on the positive aspects.", "Take a moment to breathe and reset."],
    "neutral": ["It's okay to have mixed feelings.", "Take a moment to reflect on your day.", "Sometimes it's good to just be present."],
    "unknown": ["Tell me more about how you're feeling."]
}

msg_list = SUGGESTIONS.get(st.session_state.final_mood, ["Tell me more."])
random_message = random.choice(msg_list)
st.write(random_message)

# ========== Search and Display YouTube Song ==========
st.markdown("### 🎵 Recommended Song for You")

# Only search for new video if mood changed or no video cached
if st.session_state.final_mood != "unknown" and (mood_changed or not st.session_state.video_data):
    # Create query based on input method
    if input_method == "Type my feeling" and 'user_input' in locals() and user_input:
        search_query = f"{st.session_state.final_mood} music for {user_input}"
    else:
        search_query = f"{st.session_state.final_mood} music songs"
    
    # Search for YouTube video with loading indicator
    with st.spinner("Finding the perfect song for you..."):
        video_title, recommended_song = search_youtube_video(search_query, YOUTUBE_API_KEY)
        st.session_state.video_data = (video_title, recommended_song)

# Display cached video data
if st.session_state.video_data and st.session_state.video_data[1]:
    video_title, recommended_song = st.session_state.video_data
    st.markdown(f"#### Video Name: [{video_title}]({recommended_song})")
    st.video(recommended_song)
else:
    if st.session_state.final_mood != "unknown":
        st.write("Sorry, no video found for your mood. Please try a different mood.")
    else:
        st.write("Select or describe your mood to get a song recommendation!")