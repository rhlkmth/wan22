# app.py
# A Streamlit web application for the Wan 2.5 Text-to-Video model.

import streamlit as st
import fal_client
import time
import os

# ---------------------------
# Page and State Configuration
# ---------------------------
st.set_page_config(
    page_title="Wan 2.5 Video Generator",
    page_icon="🎬",
    layout="wide"
)

# ---------------------------
# Hard-coded API Key & Constants
# ---------------------------
# IMPORTANT: Replace this placeholder with your actual fal.ai API key.
# You can get a key from https://fal.ai/
# For security, it's better to use Streamlit secrets or environment variables.
DEFAULT_FAL_KEY = "FAL_KEY_HERE"

MODEL_ID = "fal-ai/wan-25-preview/text-to-video"

# Model-specific options from the documentation
ASPECT_RATIOS = ["16:9", "9:16", "1:1"]
RESOLUTIONS = ["1080p", "720p", "480p"]
DURATIONS = ["5", "10"]

def format_aspect_ratio_with_icon(ratio: str) -> str:
    """Adds an icon and label to an aspect ratio string for the UI."""
    try:
        width, height = map(int, ratio.split(':'))
        if width > height:
            return f"🖥️ {ratio} (Landscape)"
        elif height > width:
            return f"📱 {ratio} (Portrait)"
        else:
            return f"🖼️ {ratio} (Square)"
    except ValueError:
        return ratio

# Initialize session state to store results
if 'results' not in st.session_state:
    st.session_state.results = []

# ---------------------------
# UI Layout Structure
# ---------------------------
st.title("🎬 Wan 2.5 AI Video Generator")
st.markdown("Generate high-quality videos from text prompts using the Wan 2.5 model on [fal.ai](https://fal.ai).")

left_col, right_col = st.columns([0.4, 0.6])

with left_col:
    st.header("1. Configure Your Video")

    # --- Main Inputs ---
    st.subheader("Enter a Prompt")
    prompt = st.text_area(
        "Prompt",
        "A majestic white dragon soaring through a sky filled with vibrant auroras, cinematic, detailed, 8K.",
        height=100,
        label_visibility="collapsed"
    )

    # --- Core Settings ---
    st.subheader("Adjust Settings")
    settings_col1, settings_col2 = st.columns(2)

    with settings_col1:
        formatted_ratios = [format_aspect_ratio_with_icon(r) for r in ASPECT_RATIOS]
        selected_formatted_ratio = st.selectbox("Aspect Ratio", formatted_ratios, index=0)
        # Extract the raw ratio "16:9" from the formatted string "🖥️ 16:9 (Landscape)"
        aspect_ratio = selected_formatted_ratio.split(" ")[1]

        resolution = st.selectbox("Resolution", RESOLUTIONS, index=0)

    with settings_col2:
        duration = st.selectbox("Video Length (seconds)", DURATIONS, index=0)
        seed = st.number_input("Seed (-1 for random)", value=-1, step=1)

    # --- Advanced Settings ---
    with st.expander("Advanced Settings"):
        negative_prompt = st.text_area("Negative Prompt (what to avoid)", "low quality, blurry, watermark, text")
        audio_url = st.text_input("Audio URL (optional)", placeholder="https://.../music.mp3")
        enable_prompt_expansion = st.checkbox("Enable Prompt Expansion (for short prompts)", value=True)
        custom_api_key = st.text_input("Enter your fal.ai API Key (optional)", type="password", placeholder="key_id:key_secret")

    # Determine which API key to use
    api_key_to_use = custom_api_key if custom_api_key else DEFAULT_FAL_KEY

    st.divider()

# --- Generate Button and Logic ---
if st.button("🚀 Generate Video", use_container_width=True, type="primary"):
    if not api_key_to_use or ":" not in api_key_to_use:
        st.error("Please provide a valid fal.ai API key in the advanced settings.")
    elif not prompt:
        st.error("A prompt is required to generate a video.")
    else:
        try:
            # Set the key for the fal_client
            os.environ['FAL_KEY'] = api_key_to_use

            # Prepare the arguments for the API call based on UI inputs
            api_args = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "duration": duration,
                "enable_prompt_expansion": enable_prompt_expansion,
            }
            if negative_prompt:
                api_args["negative_prompt"] = negative_prompt
            if audio_url:
                api_args["audio_url"] = audio_url
            if seed != -1:
                api_args["seed"] = seed

            # --- THIS IS THE ADDED LINE ---
            # Disable the safety checker as requested
            api_args["enable_safety_checker"] = False
            # -----------------------------

            # Show a spinner during generation
            with st.spinner(f"Generating with `{MODEL_ID}`... This can take a few minutes."):
                st.write("API Arguments being sent:") # Optional: for debugging
                st.json(api_args)                     # Optional: for debugging
                result = fal_client.subscribe(MODEL_ID, arguments=api_args)

            # Process the result from the API
            if result and 'video' in result and 'url' in result['video']:
                st.session_state.results.insert(0, {
                    "url": result['video']['url'],
                    "seed": result.get('seed', 'N/A'),
                    "prompt": prompt,
                    "actual_prompt": result.get('actual_prompt')
                })
                st.success("✅ Video generated successfully!")
                time.sleep(1) # Brief pause to let user see the success message
                st.rerun() # Rerun the app to display the new video immediately
            else:
                st.error("Generation failed. The API did not return a valid video.")
                st.json(result) # Display the raw API response for debugging

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

with right_col:
    st.header("2. View Results")

    if not st.session_state.results:
        st.info("Your generated videos will appear here.")
    else:
        # Display each generated video
        for idx, res in enumerate(st.session_state.results):
            st.video(res["url"])
            with st.expander("View Details"):
                st.text(f"Original Prompt: {res['prompt']}")
                if res['actual_prompt']:
                    st.text(f"Expanded Prompt: {res['actual_prompt']}")
                st.text(f"Seed: {res['seed']}")

            # Provide a download button for the video
            st.download_button(
                label="⬇️ Download Video",
                data=requests.get(res["url"]).content,
                file_name=f"generated_video_{idx+1}.mp4",
                mime="video/mp4",
                key=f"download_{idx}",
                use_container_width=True
            )
            st.divider()
