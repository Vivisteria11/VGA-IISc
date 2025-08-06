import os
import json
import time
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
import datetime

from google import genai
from google.genai import types
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

class StoryImageGenerator:
    def __init__(self):
        self.genai_client = genai.Client(api_key=api_key)

       

        self.story_prompt = PromptTemplate.from_template(
    """  
    You are a creative story writer and art director. Your task is to generate a JSON object by following these steps precisely:

    **Step 1. Write the Storyline:** First, write an engaging "storyline" of about 300 words based on the provided Topic, Description, and Style.
    **Step 2. Define the Characters:** After writing the storyline, identify every character and create the "character_descriptions" list. Each character must have a "name", "traits", and "appearance".
    **Step 3. Extract Key Backgrounds:** Now, **re-read the storyline you just wrote.** Identify five key, distinct physical locations that appear in the story's progression. For each location, write a visually rich description to create the "background_descriptions" list.

    **CRITICAL RULE FOR "background_descriptions":**
    - The purpose of these descriptions is to create **EMPTY background images** for later use. Therefore, they **MUST NOT** contain any characters, people, creatures, or figures.
    - Describe the physical environment ONLY. Set the stage.
    - **GOOD EXAMPLE:** "A sunlit archery range with several straw targets in the distance and a rack of bows to the side."
    - **BAD EXAMPLE:** "Kaelen is at the archery range."
    - Ensure the five descriptions offer variety and match the narrative flow of the storyline.

    Strictly adhere to this JSON format:
    {{
      "storyline": "...",
      "character_descriptions": [ {{"name": "...", "traits": "...", "appearance": "..."}} ],
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
            "topic": topic, "description": description, "style": style
        })
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            story_data = json.loads(response_text[start:end])
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
        contents = f"""
        Create a high-quality character concept art of a single character With just that person in the final output.
        **Character Name:** {name}
        **Art Style:** {style}
        **Character Appearance:** {appearance}
        **Crucial Background Instructions:**
        - The background MUST be a solid, plain white color.
        - There should be absolutely no other elements, objects, shadows, or ground textures in the background.
        - The output should be the character isolated on a **pure white background**, in a **neutral standing** pose.
        """
        print(f"\nGenerating image for {name}...")
        try:
            response = self.genai_client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=contents,
                config=types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE'])
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image = Image.open(BytesIO(part.inline_data.data))
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    sanitized_name = name.replace(' ', '_').lower()
                    filename = f"char_{sanitized_name}_{timestamp}.png"
                    image.save(filename)
                    print(f"Image generated successfully for {name}: {filename}")
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
            
            contents = f"""
            Generate a high-quality background illustration to be used as a 'background plate' in a composite scene.

            **Art Style:** {style}
            **Scene Description:** "{desc}"

            **CRITICAL COMPOSITION RULES:**
            1.  **Create Open Space:** The absolute priority is to create a scene with significant open space (negative space) in the foreground or mid-ground. This empty area is where characters will be placed later. Think of it as setting a stage for actors; the stage needs an open area for the performance.
            2.  **Framing:** The composition must be a medium shot or wide shot to provide a clear view of the environment and the open space.
            3.  **Avoid Central Clutter:** Do NOT place a large, detailed, or eye-catching object directly in the center of the frame. The main focus of the background should be off-center to leave room.
            4.  **No Figures:** The image MUST be an environment/landscape ONLY. There must be ABSOLUTELY NO people, characters, figures, or creatures.

            The final image must look like a beautiful but intentionally incomplete scene, ready for the main characters to be added.
            """
            try:
                response = self.genai_client.models.generate_content(
                    model="gemini-2.0-flash-preview-image-generation",
                    contents=contents,
                    config=types.GenerateContentConfig(response_modalities=['TEXT', 'IMAGE'])
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        image = Image.open(BytesIO(part.inline_data.data))
                        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                        filename = f"bg_{i + 1}_{timestamp}.png"
                        image.save(filename)
                        print(f"Background image {i + 1} saved: {filename}")
                        generated_files.append(filename)
                        time.sleep(1)
                        break
            except Exception as e:
                print(f"Error generating background image {i + 1}: {e}")
            
        return generated_files

    
    
    def generate_scene_descriptions(self, storyline, characters, style, background_descriptions):
        """
        Generates 9 scene descriptions by mapping them to a provided list of background settings.
        """
        print("\nGenerating scene descriptions by mapping them to available backgrounds...")

       
        scene_prompt = PromptTemplate.from_template("""
You are a meticulous scene director and visual storyteller. Your task is to generate EXACTLY 9 rich, visually grounded scene descriptions based on a STORYLINE. You must place the specified CHARACTERS into the available BACKGROUNDS.

**Your Available Tools:**
1.  **STORYLINE:** The overall plot to follow.
2.  **CHARACTERS:** The cast you can use in the scenes.
3.  **BACKGROUNDS:** A list of pre-defined locations. You MUST use these and only these locations for the scenes.

**Critical Instructions:**
- For each of the 9 scenes, **you must select the most logical background from the provided list**. A background can be reused if the story stays in one place.
- For each scene, **decide which characters from the CHARACTERS list are present**. Not all characters need to be in every scene.
- Describe **clearly what is happening** in the scene, ensuring it connects to the previous scene.
- For each character present, describe their **physical location, actions, and body language** within the chosen background.
- Specify **relative positions** of characters to each other and to key elements within the chosen background.

**Output Format (Strict JSON):**
{{
  "scenes": [
    "Scene 1: [Briefly name the chosen background here] A detailed description of the scene...",
    "Scene 2: [Briefly name the chosen background here] A detailed description of the scene...",
    ...
  ]
}}

---
**INPUTS:**

**STORYLINE:**
{storyline}

**CHARACTERS (The Cast):**
{characters}

**AVAILABLE BACKGROUNDS (The Locations):**
{background_descriptions}

**ART STYLE:**
{style}
""")

        scene_chain = scene_prompt | self.llm | StrOutputParser()
        
        try:
            # We use json.dumps to pass the lists as clean strings into the prompt.
            response_text = scene_chain.invoke({
                "storyline": storyline,
                "characters": json.dumps(characters, indent=2),
                "style": style,
                "background_descriptions": json.dumps(background_descriptions, indent=2)
            })
            
            # Find and parse the JSON block from the response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start == -1 or end == 0:
                raise json.JSONDecodeError("No JSON object found in the response.", response_text, 0)
            
            scenes_data = json.loads(response_text[start:end])

            print("\n--- Generated Scene Descriptions (Mapped to Backgrounds) ---")
            print(json.dumps(scenes_data, indent=2))
            print("----------------------------------------------------------\n")
            return scenes_data
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Error parsing scenes JSON: {e}")
            print(f"LLM Response was:\n---\n{response_text}\n---")
            return None
        

    def generate_scene_image_with_references(self, scene_description, style, character_images_bytes, background_image_byte, scene_index=0):
        print(f"\nGenerating scene image {scene_index + 1}...")

        # This stricter prompt ensures character positions are respected
        prompt_parts = [
            f"Create a high-quality composite illustration in **{style}** style.",
            f"Scene description: \"{scene_description}\"",

            "\n**Composition & Consistency Rules:**",
            "1. **Fixed Background**: Use the provided image as the definitive, unchangeable background. Do not add or remove any background elements.",
            "2. **Accurate Character Placement**: Place the characters **exactly as described**, matching their **locations, actions, and spatial relationships** in the scene description.",
            "3. **Perspective & Depth**: Match the perspective and scale of the characters to the background. Characters closer to the foreground should appear larger; those farther should appear smaller.",
            "4. **Lighting Alignment**: Match character lighting and shadows to the background's light source (e.g., sunlight direction, ambient lighting).",
            "5. **Surface Interaction**: Characters must interact with the environment realistically — sitting on chairs, leaning against trees, standing on the ground, etc.",
            "6. **Shadow Casting**: Add realistic shadows beneath characters to make them feel naturally integrated into the scene.",
            "7. **No Floating Figures**: Characters must appear firmly grounded, never hovering or clipping through surfaces.",
            "8. **Character Consistency**: Do NOT swap character identities or positions. Maintain accurate facial features, clothing, and posture throughout scenes.",
            "9. **No Additional Characters**: Do NOT add any new characters or figures that are not described in the scene.DO NOT Duplicate a character once added into the scene",
            "10. Utilize the bakcground efficiently to place the characters in a **LOGICAL** way such that it doesnt look disproportionate or out of place.",
            "11. **Character Continuity Across Scenes:** Maintain the same identity, outfit, hairstyle, and visual style for each character throughout all generated scenes. Do not change or swap appearances between frames.",


            "\nUse this image as the background:",
            Image.open(BytesIO(background_image_byte)),

            "Place these characters consistently within the scene:",
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
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = f"scene_{scene_index + 1}_{timestamp}.png"
                    image.save(filename)
                    print(f"Scene image saved: {filename}")
                    return filename
            return None
        except Exception as e:
            print(f"Error generating scene image for Scene {scene_index + 1}: {e}")
            return None