
import os
import json
import time
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

from google import genai
from google.genai import types
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

# Load environment variables from .env
load_dotenv()

# Get Gemini API key from environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

class StoryImageGenerator:
    def __init__(self):
        # Initialize clients
        self.genai_client = genai.Client(api_key=api_key)

        # Story generation setup
        self.story_prompt = PromptTemplate.from_template(
            """
            You are a creative and compelling story writer. Given a specific topic, story description, and style, generate the following JSON object:

            1.  **"storyline"**: An elaborate 300-word storyline matching the user's description and style.
            2.  **"character_descriptions"**: A list of characters. For EACH character in the list, you MUST provide a dictionary containing these EXACT keys: "name", "traits", and "appearance".
            3.  **"background_descriptions"**: A list of five distinct background scene descriptions focusing only on the environment.
            
            Strictly adhere to this JSON format:
            {{
              "storyline": "...",
              "character_descriptions": [
                {{"name": "...", "traits": "...", "appearance": "..."}},
                {{"name": "...", "traits": "...", "appearance": "..."}}
              ],
              "background_descriptions": ["...", "...", "...", "...", "..."]
            }}

            Topic: {topic}
            Story Description: {description}
            Style: {style}
            """
        )

        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.7)
        self.story_chain = self.story_prompt | self.llm | StrOutputParser()

    def generate_story_and_characters(self, topic, description, style):
        print(f"Generating story, characters, and background descriptions for topic: {topic}")
        response_text = self.story_chain.invoke({
            "topic": topic,
            "description": description,
            "style": style
        })
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            story_data = json.loads(response_text[start:end])
            
            # Print the generated JSON
            print("\n--- Generated Story and Character Data ---")
            print(json.dumps(story_data, indent=2))
            print("----------------------------------------\n")

            return story_data
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Failed to parse JSON: {e}")
            return None

    def generate_character_image(self, character, style, storyline=""):
        name = character.get("name", "Unknown_Character")
        appearance = character.get("appearance", "No appearance described")
        contents = (
            f"Create a {style} illustration of a character named {name}. "
            f"Appearance: {appearance}. "
            f"The background must be plain white with no other elements."
        )
        print(f"\nGenerating image for {name}...")
        try:
            response = self.genai_client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image = Image.open(BytesIO(part.inline_data.data))
                    filename = f"{name.replace(' ', '_').lower()}.png"
                    image.save(filename)
                    print(f"Image generated successfully for {name}")
                    return filename
            print(f"No image data received for {name}")
            return None
        except Exception as e:
            print(f"Error generating image for {name}: {e}")
            return None

    def generate_background_images(self, background_descriptions, style):
        print("\nGenerating background images...")
        generated_files = []
        for i, desc in enumerate(background_descriptions):
            print(f"Generating background image {i + 1} for description: '{desc}'")
            contents = f"Generate a background image in a {style} style. The image must ONLY be a background scene, with no characters or figures. Description: {desc}"
            try:
                response = self.genai_client.models.generate_content(
                    model="gemini-2.0-flash-preview-image-generation",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=['TEXT', 'IMAGE']
                    )
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        image = Image.open(BytesIO(part.inline_data.data))
                        filename = f"background_{i + 1}.png"
                        image.save(filename)
                        generated_files.append(filename)
                        break
            except Exception as e:
                print(f"Error generating background image {i + 1}: {e}")
        return generated_files

    def generate_scene_descriptions(self, storyline, characters, style):
        print("\nGenerating scene descriptions...")
        scene_prompt = PromptTemplate.from_template(
            """
            Based on the storyline and characters, generate 5 scene descriptions in a {style} style.
            Format output as JSON: {{"scenes": ["Description 1.", "..."]}}
            Characters: {characters}
            Storyline: {storyline}
            """
        )
        scene_chain = scene_prompt | self.llm | StrOutputParser()
        try:
            response_text = scene_chain.invoke({"storyline": storyline, "characters": json.dumps(characters), "style": style})
            scenes_data = json.loads(response_text[response_text.find("{"):response_text.rfind("}") + 1])
            
            # Print the generated JSON
            print("\n--- Generated Scene Descriptions ---")
            print(json.dumps(scenes_data, indent=2))
            print("------------------------------------\n")

            return scenes_data
        except Exception as e:
            print(f"Error parsing scenes JSON: {e}")
            return None

    def generate_scene_image_with_references(self, scene_description, style, character_images_bytes, background_image_byte, scene_index=0):
        print(f"\nGenerating scene image {scene_index + 1}...")
        prompt_parts = [
            f"Create a final, composite illustration in a {style} style. Scene Description: '{scene_description}'.",
            "Use this image as the definite background:",
            Image.open(BytesIO(background_image_byte)),
            "Place these characters consistently within the background:",
        ]
        for img_bytes in character_images_bytes:
            prompt_parts.append(Image.open(BytesIO(img_bytes)))
        try:
            response = self.genai_client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=prompt_parts,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image = Image.open(BytesIO(part.inline_data.data))
                    filename = f"scene_{scene_index + 1}.png"
                    image.save(filename)
                    return filename
            return None
        except Exception as e:
            print(f"Error generating scene image for Scene {scene_index + 1}: {e}")
            return None

    def generate_narration_and_dialogue(self, storyline, scene_descriptions):
        print("\nGenerating narration and dialogue script...")
        script_prompt = PromptTemplate.from_template(
             """
             You are a scriptwriter. Based on the storyline and scene descriptions, create narration and dialogue.
             Format as JSON: {{"script": [{{"scene": 1, "narration": "...", "dialogue": "..."}}]}}
             STORYLINE: {storyline}
             SCENES: {scene_descriptions}
             """
        )
        script_chain = script_prompt | self.llm | StrOutputParser()
        try:
            response_text = script_chain.invoke({"storyline": storyline, "scene_descriptions": json.dumps(scene_descriptions)})
            script_data = json.loads(response_text[response_text.find("{"):response_text.rfind("}") + 1])
            
            # Print the generated JSON
            print("\n--- Generated Narration and Dialogue ---")
            print(json.dumps(script_data, indent=2))
            print("----------------------------------------\n")

            return script_data
        except Exception as e:
            print(f"Error generating narration script: {e}")
            return None
    
    def generate_background_audio_description(self, scene_description, scene_index):
        print(f"\nGenerating audio description for scene {scene_index + 1}...")
        audio_prompt = PromptTemplate.from_template(
            """
            You are a sound designer. Describe the background music and SFX for this scene.
            Format as JSON: {{"audio_description": "..."}}
            SCENE: "{scene_description}"
            """
        )
        audio_chain = audio_prompt | self.llm | StrOutputParser()
        try:
            response_text = audio_chain.invoke({"scene_description": scene_description})
            audio_data = json.loads(response_text[response_text.find("{"):response_text.rfind("}") + 1])

            # Print the generated JSON
            print(f"\n--- Audio Description for Scene {scene_index + 1} ---")
            print(json.dumps(audio_data, indent=2))
            print("-------------------------------------------\n")

            return audio_data
        except Exception as e:
            print(f"Error generating audio description for scene {scene_index + 1}: {e}")
            return None