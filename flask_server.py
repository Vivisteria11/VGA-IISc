import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from story_generator import StoryImageGenerator
import base64
from flask import send_from_directory


load_dotenv()


app = Flask(__name__)
generator = StoryImageGenerator()


@app.route('/generate-story', methods=['POST'])
def handle_generate_story():
    """Generates a storyline and character descriptions."""
    data = request.get_json()
    if not data or not all(k in data for k in ['topic', 'description', 'style']):
        return jsonify({"error": "Missing required fields: topic, description, style"}), 400

    result = generator.generate_story_and_characters(data['topic'], data['description'], data['style'])

    if result:
        return jsonify(result)
    return jsonify({"error": "Story generation failed"}), 500


@app.route('/generate-character-image', methods=['POST'])
def handle_generate_character_image():
    """Generates a single character image with a plain white background."""
    data = request.get_json()
    if not data or not all(k in data for k in ['character', 'style']):
        return jsonify({"error": "Missing required fields: character, style"}), 400

    character = data['character']
    style = data['style']

    # Force a plain white background for this endpoint
    character['background_scene'] = "plain white background"

    # The 'storyline' argument is not used in the image prompt, so pass an empty string
    image_filename = generator.generate_character_image(character, style, storyline="")

    if image_filename:
        return jsonify({"message": "Image generated successfully", "filename": image_filename})
    return jsonify({"error": "Image generation failed"}), 500

@app.route('/generate-scene-descriptions', methods=['POST'])
def api_generate_scene_descriptions():
    """
    Takes a storyline, character list, and style to generate scene descriptions.
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['storyline', 'characters', 'style']):
        return jsonify({"error": "Missing fields: storyline, characters, and style"}), 400
    
    # Call the corresponding generator function
    result = generator.generate_scene_descriptions(
        data['storyline'], 
        data['characters'],
        data['style']
    )
    
    return jsonify(result) if result else (jsonify({"error": "Failed to generate scene descriptions"}), 500)


@app.route('/generate-scene-image', methods=['POST'])
def api_generate_scene_image():
    """
    Takes a scene description, style, and character images to generate a scene image.
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['scene_description', 'style', 'character_images']):
        return jsonify({"error": "Missing fields: scene_description, style, character_images"}), 400
        
    try:
        # Decode the list of Base64 strings into a list of bytes
        images_bytes = [base64.b64decode(img_str) for img_str in data['character_images']]
    except Exception as e:
        return jsonify({"error": f"Invalid Base64 image data: {e}"}), 400
        
    # Call the corresponding generator function
    filename = generator.generate_scene_image_with_references(
        data['scene_description'], 
        data['style'], 
        images_bytes, 
        data.get('scene_index', 0)  # Use an index from the payload or default to 0
    )
    
    return jsonify({"filename": filename}) if filename else (jsonify({"error": "Failed to generate scene image"}), 500)

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serves an image from the project directory."""
    return send_from_directory('.', filename)

if __name__ == "__main__":
    app.run(debug=True, port=5000)