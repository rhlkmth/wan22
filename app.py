# app.py
# A multi-modal Streamlit web application for fal.ai models.
# Supports: Text to Video, Image to Video, Text to Image, Image to Image.

import streamlit as st
import fal_client
import time
import requests
import os

# ---------------------------
# Page and State Configuration
# ---------------------------
st.set_page_config(
    page_title="Multi-Modal AI Generator",
    page_icon="🎨",
    layout="wide"
)

# ---------------------------
# API Key & Model Definitions
# ---------------------------
# IMPORTANT: Replace this placeholder with your actual fal.ai API key.
# For security, use Streamlit secrets: [server] secret = "YOUR_FAL_KEY"
DEFAULT_FAL_KEY = os.environ.get("FAL_KEY", "FAL_KEY_HERE")

MODELS = {
    "Text to Video": {
        "id": "fal-ai/wan-25-preview/text-to-video",
        "type": "text-to-video",
        "output": "video"
    },
    "Image to Video": {
        "id": "fal-ai/seed-1-image-to-video",
        "type": "image-to-video",
        "output": "video"
    },
    "Text to Image": {
        "id": "fal-ai/stable-diffusion-xl-lightning",
        "type": "text-to-image",
        "output": "image"
    },
    "Image to Image": {
        "id": "fal-ai/sdxl-img2img",
        "type": "image-to-image",
        "output": "image"
    },
}

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = []
if 'uploaded_file_data' not in st.session_state:
    st.session_state.uploaded_file_data = None

# ---------------------------
# Helper Functions
# ---------------------------
@st.cache_data(show_spinner="Downloading result...")
def download_file(url: str) -> bytes:
    """Downloads a file from a URL and returns its content."""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        st.error(f"Failed to download file: {e}")
        return b""

def upload_image_to_fal(file_data: bytes, content_type: str, api_key: str):
    """Uploads image data to fal.ai's storage and returns the URL."""
    client = fal_client.SyncClient(key=api_key)
    file_url = client.upload(file_data, content_type=content_type)
    return file_url

# ---------------------------
# UI Layout Structure
# ---------------------------
st.title("🎨 Multi-Modal AI Generator")
st.markdown("Create stunning visuals from text or images using a suite of powerful AI models on [fal.ai](https://fal.ai).")

left_col, right_col = st.columns([0.4, 0.6])

with left_col:
    st.header("1. Configure Your Generation")

    # --- Mode Selector ---
    selected_mode = st.selectbox(
        "**Select Generation Mode**",
        list(MODELS.keys()),
        help="Choose between creating videos or images, from text or an initial image."
    )
    model_config = MODELS[selected_mode]
    model_id = model_config["id"]
    model_type = model_config["type"]
    output_type = model_config["output"]

    # --- Image Input (Conditional) ---
    image_input_needed = model_type in ["image-to-video", "image-to-image"]
    image_url_from_input = None

    if image_input_needed:
        st.subheader("Upload an Image")
        uploaded_file = st.file_uploader(
            "Drag and drop your starting image here",
            type=["png", "jpg", "jpeg", "webp"],
            key="start_frame_uploader"
        )
        if uploaded_file:
            st.session_state.uploaded_file_data = {
                "name": uploaded_file.name,
                "type": uploaded_file.type,
                "data": uploaded_file.getvalue()
            }
        
        with st.expander("Or use a public URL"):
            image_url_from_input = st.text_input("Image URL", placeholder="https://...")
            if image_url_from_input:
                st.session_state.uploaded_file_data = None # Prioritize URL if provided
        st.divider()
    else:
        st.session_state.uploaded_file_data = None

    # --- Common Inputs ---
    st.subheader("Enter a Prompt")
    prompt = st.text_area(
        "Prompt",
        "A cinematic shot of a futuristic city at sunset, neon lights reflecting on wet streets.",
        height=100,
        label_visibility="collapsed"
    )

    st.subheader("Adjust Settings")
    settings_col1, settings_col2 = st.columns(2)
    with settings_col1:
        if "video" in model_type:
            duration = st.select_slider("Video Length (s)", options=[*range(3, 11)], value=5)
        resolution = st.selectbox("Resolution / Aspect Ratio",
                                  ["1024x1024", "1280x720 (16:9)", "720x1280 (9:16)", "1024x576"],
                                  index=0)
    with settings_col2:
        seed = st.number_input("Seed (-1 for random)", value=-1, step=1)

    # --- Advanced Settings ---
    audio_url = None  # Initialize audio_url outside the expander
    strength = 0.75   # Default strength value
    
    with st.expander("Advanced Settings"):
        if model_type == "image-to-image":
            strength = st.slider("Strength", 0.0, 1.0, 0.75, help="How much noise to add to the input image.")
        if "video" in model_type:
            audio_url = st.text_input("Audio URL (optional)", placeholder="https://.../music.mp3")
        negative_prompt = st.text_area("Negative Prompt", "blurry, low quality, bad anatomy, watermark")
        custom_api_key = st.text_input("Enter your fal.ai API Key (optional)", type="password")

    api_key_to_use = custom_api_key if custom_api_key else DEFAULT_FAL_KEY
    st.divider()

    # --- Generation Button and Logic ---
    if st.button(f"🚀 Generate {output_type.capitalize()}", use_container_width=True, type="primary"):
        if not api_key_to_use or ":" not in api_key_to_use:
            st.error("Please provide a valid fal.ai API key in the advanced settings.")
        elif image_input_needed and not st.session_state.uploaded_file_data and not image_url_from_input:
            st.error("This mode requires a starting image. Please upload one or provide a URL.")
        elif not prompt:
            st.error("A prompt is required.")
        else:
            try:
                os.environ['FAL_KEY'] = api_key_to_use
                final_image_url = image_url_from_input

                with st.spinner("Preparing assets..."):
                    if st.session_state.uploaded_file_data:
                        file_info = st.session_state.uploaded_file_data
                        final_image_url = upload_image_to_fal(file_info["data"], file_info["type"], api_key_to_use)

                with st.spinner(f"Generating with `{model_id}`... This may take a minute."):
                    # Base arguments for all models
                    api_args = {"prompt": prompt}
                    if negative_prompt:
                        api_args["negative_prompt"] = negative_prompt
                    if seed != -1:
                        api_args["seed"] = seed

                    # Model-specific arguments
                    if model_type == "text-to-video":
                        api_args.update({
                            "aspect_ratio": "16:9" if "16:9" in resolution else "9:16" if "9:16" in resolution else "1:1",
                            "resolution": "1080p",
                            "duration": str(duration),
                            "enable_safety_checker": False
                        })
                        if audio_url:  # Fixed: removed 'audio_url' in locals() check
                            api_args["audio_url"] = audio_url
                    elif model_type == "image-to-video":
                        width, height = map(int, resolution.split('x')[0:2])  # Fixed: handle resolution parsing better
                        api_args.update({
                            "image_url": final_image_url, 
                            "width": width, 
                            "height": height,
                            "enable_safety_checker": False  # Added: disable safety checker for image-to-video
                        })
                    elif model_type == "image-to-image":
                        api_args.update({
                            "image_url": final_image_url, 
                            "strength": strength,
                            "enable_safety_checker": False  # Added: disable safety checker for image-to-image
                        })
                    elif model_type == "text-to-image":
                        api_args["enable_safety_checker"] = False  # Added: disable safety checker for text-to-image

                    # Call the API
                    result = fal_client.subscribe(model_id, arguments=api_args)

                    # Process result
                    output_data = None
                    if output_type == "video" and result.get('video'):
                        output_data = result['video']
                    elif output_type == "image" and result.get('images'):
                        output_data = result['images'][0]  # Take the first image

                    if output_data:
                        st.session_state.results.insert(0, {
                            "url": output_data['url'],
                            "type": output_type,
                            "seed": result.get('seed', 'N/A'),
                            "prompt": prompt
                        })
                        st.success(f"✅ {output_type.capitalize()} generated successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Generation failed. API did not return a valid result.")
                        st.json(result)

            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

with right_col:
    st.header("2. View Results")
    if image_input_needed and st.session_state.uploaded_file_data:
        st.image(st.session_state.uploaded_file_data["data"], caption="Current Start Image Preview", use_container_width=True)

    if not st.session_state.results:
        st.info("Your generated creations will appear here.")
    else:
        for idx, res in enumerate(st.session_state.results):
            try:
                if res["type"] == "video":
                    st.video(res["url"])
                    file_name = f"generated_video_{idx+1}.mp4"
                    mime = "video/mp4"
                else:  # image
                    st.image(res["url"])
                    file_name = f"generated_image_{idx+1}.png"
                    mime = "image/png"

                st.caption(f"Prompt: {res['prompt']} | Seed: {res['seed']}")
                
                # Download file content
                file_bytes = download_file(res["url"])
                if file_bytes:  # Only show download button if file was successfully downloaded
                    st.download_button(
                        label=f"⬇️ Download {res['type'].capitalize()}",
                        data=file_bytes,  # Fixed: use file_bytes instead of requests.get
                        file_name=file_name,
                        mime=mime,
                        key=f"download_{idx}",
                        use_container_width=True
                    )
                st.divider()
            except Exception as e:
                st.error(f"Error displaying result {idx+1}: {e}")
                st.divider()
