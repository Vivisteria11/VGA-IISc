
import requests
import json
import base64
import time
import os

# --- Configuration ---
BASE_URL = "http://127.0.0.1:5000"
# OUTPUTS_DIR has been removed.

# --- Helper Functions ---
def make_post_request(endpoint, payload):
    """A helper function to make POST requests and handle responses."""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        print(f"SUCCESS: POST request to {endpoint} was successful.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request to {endpoint} failed: {e}")
        if e.response is not None:
            print(f"--> Server Response: {e.response.text}")
        return None

def read_image_as_base64(filename):
    """Reads an image file from the main project directory and encodes it to Base64."""
    # The filepath is now just the filename, since we're in the same directory.
    try:
        with open(filename, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"ERROR: Could not find file {filename} to encode.")
        return None

# --- Main Test Execution ---
def main():
    """Runs the full end-to-end story generation pipeline by calling the API."""
    print("--- Starting API Test Pipeline ---")

    story_payload = {
    "topic": "The Electric Circuit Adventure",
    "description": "Meet Volt, a curious little electron who lives in a battery. One day, the Switch turns ON, and Volt zooms out to explore the circuit! He races through wires, powers a glowing bulb, and learns how electricity flows. Along the way, he meets Resi the Resistor, who teaches him how some things slow down electricity, and Cap the Capacitor, who stores energy. With fun surprises in every panel, Volt shows how all the parts of a simple circuit work together to light things up!",
    "style": "Simple  comic book style with bold lines, cheerful characters, and clear science visuals. "
    }


    
    # --- STEP 1: Generate Story, Characters, and Background Descriptions ---
    print("\n## STEP 1: GENERATING STORY DATA ##")
    story_data = make_post_request('/generate-story', story_payload)
    time.sleep(2)
    if not story_data: return

    storyline = story_data.get("storyline")
    character_descriptions = story_data.get("character_descriptions")
    background_descriptions = story_data.get("background_descriptions")

    # --- STEP 2: Generate Character Images ---
    print("\n## STEP 2: GENERATING CHARACTER IMAGES ##")
    character_image_files = []
    for char in character_descriptions:
        payload = {"character": char, "style": story_payload['style']}
        result = make_post_request('/generate-character-image', payload)
        time.sleep(2)
        if result and result.get("filename"):
            character_image_files.append(result["filename"])

    # --- STEP 3: Generate Background Images ---
    print("\n## STEP 3: GENERATING BACKGROUND IMAGES ##")
    payload = {"background_descriptions": background_descriptions, "style": story_payload['style']}
    result = make_post_request('/generate-background-images', payload)
    time.sleep(2)
    background_image_files = result.get("filenames", []) if result else []

    # --- STEP 4: Generate Scene Descriptions ---
    print("\n## STEP 4: GENERATING SCENE DESCRIPTIONS ##")
    payload = {"storyline": storyline, "characters": character_descriptions, "style": story_payload['style']}
    scenes_data = make_post_request('/generate-scene-descriptions', payload)
    time.sleep(2)
    if not scenes_data: return
    scene_descriptions_list = scenes_data.get("scenes", [])

    # --- STEP 5: Generate Scene Images ---
    print("\n## STEP 5: GENERATING SCENE IMAGES ##")
    scene_image_files = []
    char_images_b64 = [read_image_as_base64(f) for f in character_image_files if f]
    for i, desc in enumerate(scene_descriptions_list):
        if not background_image_files:
            print("Skipping scene image generation due to missing background images.")
            break
        bg_image_b64 = read_image_as_base64(background_image_files[i % len(background_image_files)])
        if not char_images_b64 or not bg_image_b64:
            print(f"Skipping scene {i+1} due to missing image assets.")
            continue
        payload = {
            "scene_description": desc,
            "style": story_payload['style'],
            "character_images_base64": char_images_b64,
            "background_image_base64": bg_image_b64,
            "scene_index": i
        }
        result = make_post_request('/generate-scene-image', payload)
        time.sleep(2)
        if result and result.get("filename"):
            scene_image_files.append(result["filename"])

    # --- STEP 6: Generate Script ---
    print("\n## STEP 6: GENERATING SCRIPT ##")
    payload = {"storyline": storyline, "scene_descriptions": scene_descriptions_list}
    script_data = make_post_request('/generate-script', payload)
    time.sleep(2)
    if not script_data: return

    # --- STEP 7: Generate Audio Descriptions ---
    print("\n## STEP 7: GENERATING AUDIO DESCRIPTIONS ##")
    audio_assets = []
    for i, desc in enumerate(scene_descriptions_list):
        payload = {"scene_description": desc, "scene_index": i}
        result = make_post_request('/generate-audio-description', payload)
        time.sleep(2)
        if result:
            audio_assets.append(result)

    
    # --- Final Summary ---
    print("\n--- API TEST PIPELINE COMPLETE ---")
    print("The following assets were generated by the server:")
    print(f"\nCharacter Images: {character_image_files}")
    print(f"Background Images: {background_image_files}")
    print(f"Scene Images: {scene_image_files}")
    print("\nAll generated files are in your main project directory.")

if __name__ == "__main__":
    main()
