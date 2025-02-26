import streamlit as st
import json
import os
from pytube import extract
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="YouTube Workout Extractor",
    page_icon="💪",
    layout="wide"
)

# Load environment variables
load_dotenv()  # Load API key from .env file

# Use environment variable for API key
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

# Functions


def extract_video_id(url):
    """Extracts the YouTube video ID from a URL using pytube."""
    try:
        return extract.video_id(url)
    except Exception as e:
        st.error(f"Error extracting video ID: {e}")
        return None


def get_transcript(video_id):
    """Gets transcript for a YouTube video using the video ID."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        available_transcripts = {}

        for transcript in transcript_list:
            available_transcripts[transcript.language] = {
                "language": transcript.language,
                "is_generated": transcript.is_generated
            }

        # Try to get English transcript first
        if "en" in available_transcripts:
            return transcript_list.find_transcript(["en"]).fetch()
        # If not available, get the first available transcript
        else:
            return list(transcript_list)[0].fetch()
    except Exception as e:
        st.error(f"Error getting transcript: {e}")
        return None


def extract_workout_perplexity(transcript):
    """Extracts workout details from transcript using Perplexity AI."""
    if not transcript:
        st.warning("No transcript available for this video.")
        return None

    transcript_text = " ".join([entry["text"] for entry in transcript])

    prompt = f"""
    Extract workout details (exercise name, sets, reps) from the following transcript:
    {transcript_text}

    Return just the result as a JSON list with this structure:
    [
        {{"exercise": "Push-ups", "sets": 3, "reps": 15}},
        {{"exercise": "Squats", "sets": 4, "reps": 12}}
    ]
    
    Please do not add anything else, simply return the JSON list. This includes adding markdown formatting.
    """

    messages = [
        {"role": "system", "content": "You are an assistant that extracts workout details. You will extract information related to exercises, sets, and reps. You will only get information about exercises related to weightlifting or bodyweight exercises."},
        {"role": "user", "content": prompt}
    ]

    try:
        if not PERPLEXITY_API_KEY:
            st.error(
                "Perplexity API key is missing. Please add it to your .env file.")
            return None

        client = OpenAI(
            api_key=PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai"
        )

        with st.spinner("Analyzing workout content..."):
            response = client.chat.completions.create(
                model="sonar",
                messages=messages,
            )
    except Exception as e:
        st.error(f"Failed to connect to Perplexity API: {e}")
        return None

    # Extract JSON from Perplexity response
    extracted_data = response.choices[0].message.content

    try:
        return json.loads(extracted_data)
    except json.JSONDecodeError:
        st.error("Failed to parse Perplexity response as JSON.")
        return None


def embed_youtube_video(video_id):
    """Creates an embedded YouTube player for the video."""
    return f"""
    <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 10px;">
        <iframe src="https://www.youtube.com/embed/{video_id}" 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;" 
            allowfullscreen>
        </iframe>
    </div>
    """


# App UI
st.title("💪 YouTube Workout Plan Extractor")
st.write("Enter a YouTube video URL to extract the workout plan from the video's transcript.")

# Input for YouTube URL
youtube_url = st.text_input(
    "YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

# Process button
if st.button("Extract Workout Plan", type="primary"):
    if youtube_url:
        # Extract video ID
        video_id = extract_video_id(youtube_url)

        if video_id:
            # Display YouTube video
            st.subheader("Video")
            st.markdown(embed_youtube_video(video_id), unsafe_allow_html=True)

            # Get transcript
            with st.spinner("Getting video transcript..."):
                transcript = get_transcript(video_id)

            if transcript:
                # Extract workout details
                workout_data = extract_workout_perplexity(transcript)

                if workout_data:
                    st.subheader("Extracted Workout Plan")

                    # Convert to DataFrame for better display
                    workout_df = pd.DataFrame(workout_data)

                    # Display as styled table
                    st.dataframe(
                        workout_df,
                        column_config={
                            "exercise": "Exercise",
                            "sets": "Sets",
                            "reps": "Reps"
                        },
                        hide_index=True,
                        use_container_width=True
                    )

                    # Add download buttons
                    col1, col2 = st.columns(2)

                    with col1:
                        csv = workout_df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name="workout_plan.csv",
                            mime="text/csv"
                        )

                    with col2:
                        json_str = json.dumps(workout_data, indent=2)
                        st.download_button(
                            label="Download JSON",
                            data=json_str,
                            file_name="workout_plan.json",
                            mime="application/json"
                        )
                else:
                    st.warning(
                        "Could not extract workout plan from this video.")
            else:
                st.warning("No transcript available for this video.")
    else:
        st.warning("Please enter a YouTube URL to process.")

# App footer
st.markdown("---")
st.markdown("### How to use this app")
st.markdown("""
1. Enter a YouTube URL of a workout video
2. Click the "Extract Workout Plan" button
3. Review the extracted workout plan
4. Download the plan as CSV or JSON if needed
""")

# Sidebar with information
with st.sidebar:
    st.header("About")
    st.info("""
    This app extracts workout plans from YouTube videos using AI.
    
    It works by:
    1. Extracting the video transcript
    2. Analyzing the transcript with Perplexity AI
    3. Presenting the structured workout plan
    
    **Note:** The app requires a Perplexity API key in your .env file.
    """)

    st.header("Requirements")
    st.code("""
    pip install streamlit pytube youtube-transcript-api openai python-dotenv pandas
    """)

    st.header("Setup")
    st.markdown("""
    Create a .env file in the same directory with:
    ```
    PERPLEXITY_API_KEY=your_api_key_here
    ```
    """)
