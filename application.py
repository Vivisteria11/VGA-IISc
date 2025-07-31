import streamlit as st
import requests
import base64
import os


BASE_URL = "http://127.0.0.1:5000"
API_ENDPOINTS = {
    "story_and_chars": f"{BASE_URL}/generate-story",
    "char_image": f"{BASE_URL}/generate-character-image",
    "scene_desc": f"{BASE_URL}/generate-scene-descriptions",
    "scene_image": f"{BASE_URL}/generate-scene-image"
}
IMAGE_DIR_URL = f"{BASE_URL}/images"

if 'story_data' not in st.session_state:
    st.session_state.story_data = None
if 'character_images' not in st.session_state:
    st.session_state.character_images = []
if 'scene_descriptions' not in st.session_state:
    st.session_state.scene_descriptions = None
if 'final_scene_images' not in st.session_state:
    st.session_state.final_scene_images = []



st.set_page_config(layout="wide")
st.title("Story and Scene Image Generator")

# --- Inputs in the Sidebar ---
# --- Inputs on the Main Page ---
st.header("1. Story Inputs")
col1, col2, col3 = st.columns(3)
with col1:
    topic_input = st.text_input("Topic", "The Discovery of Fire")
with col2:
    style_input = st.text_input("Art Style", "Prehistoric cave painting style")

description_input = st.text_area("Description", "A curious cave person named Kael discovers fire by accidentally striking two stones together. At first scared, they learn to control it with their friend, Lyra.", height=150)
#button 1
if st.button("1. Generate Story and Characters", type="primary"):
    with st.spinner("Generating storyline and characters..."):
        payload = {"topic": topic_input, "description": description_input, "style": style_input}
        response = requests.post(API_ENDPOINTS["story_and_chars"], json=payload)
        if response.status_code == 200:
            st.session_state.story_data = response.json()
            st.session_state.character_images = []
            st.session_state.scene_descriptions = None
            st.session_state.final_scene_images = []
        else:
            st.error("Failed to generate story. Check the Flask server.")
            st.session_state.story_data = None

    st.divider() # Add a line to separate inputs from outputs
    
    


# Display for Step 1 Output
if st.session_state.story_data:
    st.header("Step 1 Output: Storyline and Characters")
    st.subheader("Storyline")
    st.write(st.session_state.story_data.get("storyline"))
    st.subheader("Characters")
    st.subheader("Characters")
    for char in st.session_state.story_data.get("character_descriptions", []):
        st.markdown(f"**Name:** {char.get('name')}")
        st.markdown(f"**Traits:** {char.get('traits')}")
        st.markdown(f"**Appearance:** {char.get('appearance')}")
        st.write("---")
    st.divider()

    # Button 2
    st.header("Step 2: Generate Character Images")
    if st.button("Generate Images for Characters"):
        st.session_state.character_images = [] # Clear previous images
        characters = st.session_state.story_data.get("character_descriptions", [])
        with st.spinner("Generating character images..."):
            for char in characters:
                payload = {"character": char, "style": style_input}
                response = requests.post(API_ENDPOINTS["char_image"], json=payload)
                if response.status_code == 200:
                    filename = response.json().get("filename")
                    st.session_state.character_images.append(filename)
                else:
                    st.warning(f"Could not generate image for {char.get('name')}")
    
    #Display for Step 2 Output
    if st.session_state.character_images:
        cols = st.columns(len(st.session_state.character_images))
        for i, filename in enumerate(st.session_state.character_images):
            with cols[i]:
                st.image(f"{IMAGE_DIR_URL}/{filename}", caption=filename, width = 300)
        st.divider()

    #Button 3
    st.header("Step 3: Generate Scene Descriptions")
    if st.button("Generate Scene Descriptions from Story"):
        with st.spinner("Generating scene descriptions..."):
            payload = {
                "storyline": st.session_state.story_data.get("storyline"),
                "characters": st.session_state.story_data.get("character_descriptions"),
                "style": style_input
            }
            response = requests.post(API_ENDPOINTS["scene_desc"], json=payload)
            if response.status_code == 200:
                st.session_state.scene_descriptions = response.json().get("scenes")
            else:
                st.error("Failed to generate scene descriptions.")

    #Display for Step 3 Output
    if st.session_state.scene_descriptions:
        st.subheader("Generated Scene Descriptions")
        for i, scene_desc in enumerate(st.session_state.scene_descriptions):
           st.markdown(f"**Scene {i+1}:** {scene_desc}")
        st.divider()

    #Button 4
    st.header("Step 4: Generate Scene Images")
    if st.session_state.character_images and st.session_state.scene_descriptions:
        if st.button("Generate Final Scene Images"):
            st.session_state.final_scene_images = []
            char_images_b64 = []
            for filename in st.session_state.character_images:
                if os.path.exists(filename):
                    with open(filename, "rb") as f:
                        encoded_string = base64.b64encode(f.read()).decode('utf-8')
                        char_images_b64.append(encoded_string)
            
            with st.spinner("Generating scene images with character references..."):
                for i, scene_desc in enumerate(st.session_state.scene_descriptions):
                    payload = {
                        "scene_description": scene_desc,
                        "style": style_input,
                        "character_images": char_images_b64,
                        "scene_index": i
                    }
                    response = requests.post(API_ENDPOINTS["scene_image"], json=payload)
                    if response.status_code == 200:
                        filename = response.json().get("filename")
                        st.session_state.final_scene_images.append(filename)
                    else:
                        st.warning(f"Could not generate image for Scene {i+1}")
    
    #Display for Step 4 Output
    if st.session_state.final_scene_images:
        st.subheader("Final Scene Images")
        cols = st.columns(len(st.session_state.final_scene_images), gap="medium")
        for i, filename in enumerate(st.session_state.final_scene_images):
             with cols[i]:
                st.image(f"{IMAGE_DIR_URL}/{filename}", caption=filename, width = 300)