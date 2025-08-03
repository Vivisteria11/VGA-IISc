import os
import base64
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from new import StoryImageGenerator


load_dotenv()
app = Flask(__name__)
generator = StoryImageGenerator()

def handle_error(message, status_code):
    """Returns a standardized JSON error response."""
    return jsonify({"error": message}), status_code


@app.route('/generate-story', methods=['POST'])
def api_generate_story():
    data = request.get_json()
    if not data or not all(k in data for k in ['topic', 'description', 'style']):
        return handle_error("Missing required fields: topic, description, style", 400)
    result = generator.generate_story_and_characters(data['topic'], data['description'], data['style'])
    return jsonify(result) if result else handle_error("Story generation failed on the server.", 500)

@app.route('/generate-character-image', methods=['POST'])
def api_generate_character_image():
    data = request.get_json()
    if not data or not all(k in data for k in ['character', 'style']):
        return handle_error("Missing required fields: character, style", 400)
    filename = generator.generate_character_image(data['character'], data['style'], storyline="")
    return jsonify({"filename": filename}) if filename else handle_error("Character image generation failed on the server.", 500)

@app.route('/generate-background-images', methods=['POST'])
def api_generate_background_images():
    data = request.get_json()
    if not data or not all(k in data for k in ['background_descriptions', 'style']):
        return handle_error("Missing required fields: background_descriptions, style", 400)
    filenames = generator.generate_background_images(data['background_descriptions'], data['style'])
    return jsonify({"filenames": filenames}) if filenames is not None else handle_error("Background image generation failed on the server.", 500)

@app.route('/generate-scene-descriptions', methods=['POST'])
def api_generate_scene_descriptions():
    data = request.get_json()
    if not data or not all(k in data for k in ['storyline', 'characters', 'style']):
        return handle_error("Missing required fields: storyline, characters, style", 400)
    result = generator.generate_scene_descriptions(data['storyline'], data['characters'], data['style'])
    return jsonify(result) if result else handle_error("Failed to generate scene descriptions on the server.", 500)

@app.route('/generate-scene-image', methods=['POST'])
def api_generate_scene_image():
    data = request.get_json()
    required_keys = ['scene_description', 'style', 'character_images_base64', 'background_image_base64']
    if not data or not all(k in data for k in required_keys):
        return handle_error(f"Missing required fields. Required: {required_keys}", 400)
    try:
        char_bytes = [base64.b64decode(img_str) for img_str in data['character_images_base64']]
        bg_bytes = base64.b64decode(data['background_image_base64'])
    except Exception as e:
        return handle_error(f"Invalid Base64 image data provided: {e}", 400)
    filename = generator.generate_scene_image_with_references(
        data['scene_description'], data['style'], char_bytes, bg_bytes, data.get('scene_index', 0)
    )
    return jsonify({"filename": filename}) if filename else handle_error("Failed to generate scene image on the server.", 500)

@app.route('/generate-script', methods=['POST'])
def api_generate_script():
    data = request.get_json()
    if not data or not all(k in data for k in ['storyline', 'scene_descriptions']):
        return handle_error("Missing required fields: storyline, scene_descriptions", 400)
    result = generator.generate_narration_and_dialogue(data['storyline'], data['scene_descriptions'])
    return jsonify(result) if result else handle_error("Failed to generate script on the server.", 500)

@app.route('/generate-audio-description', methods=['POST'])
def api_generate_audio_description():
    data = request.get_json()
    if not data or 'scene_description' not in data:
        return handle_error("Missing required field: scene_description", 400)
    result = generator.generate_background_audio_description(data['scene_description'], data.get('scene_index', 0))
    return jsonify(result) if result else handle_error("Failed to generate audio description on the server.", 500)




@app.route('/files/<path:filename>')
def serve_file(filename):
    """Serves any generated file from the main project directory."""
    # The '.' specifies the current directory, which is your project's root folder.
    return send_from_directory('.', filename, as_attachment=False)

#Run Application 
if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)