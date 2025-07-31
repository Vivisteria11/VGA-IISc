import os
import json
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

from google import genai
from google.genai import types
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

#  Load environment variables from .env
load_dotenv()

# Get Gemini API key from environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

class StoryImageGenerator:
    def __init__(self):
        #  Initialize Gemini client with .env-loaded key
        self.genai_client = genai.Client(api_key=api_key)

        # Story generation setup
        self.story_prompt = PromptTemplate.from_template(
            """
            You are a creative and compelling story writer. Given a specific topic, story description, and style, generate:

            1. An elaborate 300 word storyline based on facts that must match the users description. Adapt the tone and style to match the specified style: {style}.
            2. Character descriptions to blend based on the background scenes ,the character must not be naked or obscene. (Name, Traits, Appearance, Background scene).
            3.Format output as a single, clean JSON object. Ensure all special characters like newlines within string values are properly escaped (e.g., use \\n instead of a literal newline).
            Format output as a single, clean JSON object like:
            {{
              "storyline": "...",
              "character_descriptions": [{{"name": "...", "traits": "...", "appearance": "...", "background_scene": "..."}}]
            }}

            Topic: {topic}
            Story Description: {description}
            Style: {style}
            """
        )

        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.7)
        self.story_chain = self.story_prompt | self.llm | StrOutputParser()

    def generate_story_and_characters(self, topic, description, style):
        print(f"Generating story for topic: {topic}")
        response_text = self.story_chain.invoke({
            "topic": topic,
            "description": description,
            "style": style
        })

        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            story_data = json.loads(response_text[start:end])
            print(json.dumps(story_data, indent=2))
            return story_data
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Failed to parse JSON: {e}")
            return None

    def generate_character_image(self, character, style, storyline):
        name = character["name"]
        appearance = character["appearance"]
        traits = character.get("traits", "")

        #  Plain white background explicitly requested
        contents = (
            f"Create a {style} illustration of a character named {name}. "
            f"Character appearance: {appearance}. "
            f"Character personality traits: {traits}. "
            f"The background must be plain white with no other elements. "
            f"The image should be high quality and must match the style {style}. "
            f"The character must be the main focus of the image with nothing around them."
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
                if part.inline_data is not None:
                    image = Image.open(BytesIO(part.inline_data.data))
                    filename = f"{name.replace(' ', '_').lower()}_{style.replace(' ', '_')}.png"
                    image.save(filename)
                    print(f"Image generated successfully for {name}")
                    return filename

            print(f"No image data received for {name}")
            return None

        except Exception as e:
            print(f"Error generating image for {name}: {e}")
            return None
        
    def generate_scene_descriptions(self, storyline, characters, style):
        character_list_str = json.dumps(characters, indent=2)
        scene_prompt = PromptTemplate.from_template(
            """
            Based on the storyline and characters description below, generate 3-5 scene descriptions in the specified style.Do not deviate from the storyline and focus on character descriptions ,be as consistent as possible.
            Format the output as a JSON object: {{"scenes": ["Description of scene 1.", "..."]}}

            Style: {style}
            Characters:
            {characters}
            Storyline:
            {storyline}
            """
        )
        scene_chain = scene_prompt | self.llm | StrOutputParser()
        try:
            response_text = scene_chain.invoke({"storyline": storyline, "characters": character_list_str, "style": style})
            return json.loads(response_text[response_text.find("{"):response_text.rfind("}") + 1])
        except Exception as e:
            print(f"Error parsing scenes JSON: {e}")
            return None

    # --- Process 4: Generate a Single Scene's Image with References ---
    def generate_scene_image_with_references(self, scene_description, style, character_images_bytes, scene_index=0):
        prompt_parts = [
            f"Create a {style} illustration of a scene . Do not add any text or speech bubbles. ",
            f"Scene Description: '{scene_description}'. ",
            "Use the following images as a direct visual reference to ensure the characters in the scene are very much consistent with their original appearance and traits ,Do not merge characters."
        ]
        for img_bytes in character_images_bytes:
            prompt_parts.append(Image.open(BytesIO(img_bytes)))
        try:
            response = self.genai_client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=prompt_parts,
                config=types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE'])
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

generator = StoryImageGenerator()
