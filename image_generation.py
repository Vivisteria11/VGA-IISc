import os
import json
from io import BytesIO
from PIL import Image

from google import genai
from google.genai import types
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

# Configure the API key
os.environ['GOOGLE_API_KEY'] = userdata.get('GOOGLE_API_KEY')

class StoryImageGenerator:
    def __init__(self):
        # Initialize Gemini clients
        self.genai_client = genai.Client(api_key=os.environ['GOOGLE_API_KEY'])
        
        # Story generation setup
        self.story_prompt = PromptTemplate.from_template(
            """
            You are a creative and compelling story writer. Given a specific topic, story description, and style, generate:

            1. An elaborate 300 word storyline based on facts that must match the users description. Adapt the tone and style to match the specified style: {style}.
            2. Character descriptions to blend based on the background scenes (Name, Traits, Appearance, Background scene).

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
        #Langchain wrapped with LLM
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.7)
        self.story_chain = self.story_prompt | self.llm | StrOutputParser()
        
    def generate_story_and_characters(self, topic, description, style):
        """Generate story and character descriptions"""
        print(f"Generating story for topic: {topic}")
        print(f"Description: {description}")
        print(f"Style: {style}")
        
        response_text = self.story_chain.invoke({
            "topic": topic, 
            "description": description,
            "style": style
        })
        
        # Extract JSON from response
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            story_data = json.loads(response_text[start:end])
            
            # Display the JSON response
            print("\nGenerated Story and Character Data:")
            print(json.dumps(story_data, indent=2))
            
            return story_data
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Failed to parse JSON: {e}")
            return None
    
    def generate_character_image(self, character, style, storyline):
        """Generate image using Gemini's native image generation API"""
        name = character["name"]
        appearance = character["appearance"]
        background = character["background_scene"]
        traits = character.get("traits", "")
        
        # Create detailed prompt for image generation
        contents = (
            f"Create a {style} illustration of a character named {name}. "
            f"Character appearance: {appearance}. "
            f"Character personality traits: {traits}. "
            f"Background setting: {background}. "
            f"The image should be in {style} style, high quality, detailed, and vibrant. "
            f"Make sure the character is the main focus with clear, engaging features suitable for the story context."
        )
        
        print(f"\nGenerating image for {name}...")
        
        try:
            # Use the correct Gemini image generation API
            response = self.genai_client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )
            
            # Process the response
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    pass  # Ignore text response
                elif part.inline_data is not None:
                    # Save the generated image
                    image = Image.open(BytesIO(part.inline_data.data))
                    filename = f"{name.replace(' ', '_').lower()}_{style.replace(' ', '_')}.png"
                    image.save(filename)
                    print(f"Image generated successfully for {name}")
                    image.show()  # Display the image
                    return filename
            
            print(f"No image data received for {name}")
            return None
                
        except Exception as e:
            print(f"Error generating image for {name}: {e}")
            return None
    
    def process_complete_story(self, topic, description, style):
        """Complete pipeline: story generation + image generation"""
        print(f"\nPROCESSING: {topic.upper()} - {style.upper()} STYLE")
        print("="*70)
        
        # Generate story and characters
        story_data = self.generate_story_and_characters(topic, description, style)
        if not story_data:
            return None
        
        # Generate images for each character
        print(f"\nGenerating images for {len(story_data['character_descriptions'])} character(s):")
        
        generated_images = []
        for i, character in enumerate(story_data["character_descriptions"]):
            image_file = self.generate_character_image(character, style, story_data["storyline"])
            if image_file:
                generated_images.append({
                    'character': character['name'],
                    'image_file': image_file,
                    'status': 'success'
                })
            else:
                generated_images.append({
                    'character': character['name'],
                    'image_file': None,
                    'status': 'failed'
                })
        
        return {
            'story_data': story_data,
            'generated_images': generated_images,
            'topic': topic,
            'style': style
        }

# Initialize the generator
generator = StoryImageGenerator()

print("STARTING GEMINI STORY-TO-IMAGE GENERATION TESTS...")

# TEST CASE 1: Realistic/Scientific Style
print("\nTEST CASE 1")
result1 = generator.process_complete_story(
    topic="Buoyancy",
    description="A curious girl is sitting next to a tub with a soft rubber duck and a toy square block seeing which will float or sink",
    style="realistic scientific illustration"
)

# TEST CASE 2: Fantasy/Magical Style  
print("\nTEST CASE 2")
result2 = generator.process_complete_story(
      topic ="Gravity",
      description = "An apple falling from a tree next to a boy  wearing spectacles.",
      style="child friendly cartoon "
)

# TEST CASE 3: Cartoon/Children's Book Style
print("\nTEST CASE 3")
result3 = generator.process_complete_story(
    topic="Ocean Currents",
    description="Friendly sea creatures riding ocean currents in an underwater adventure", 
    style="comic book "
)

# Final Results Summary
print("\nFINAL RESULTS SUMMARY")
print("="*50)

test_cases = [
    ("Bouyancy -realistic scientific illustration", result1),
    ("Gravity - child friendly cartoon  ", result2), 
    ("Ocean Currents - comic book", result3)
]

for i, (test_name, result) in enumerate(test_cases, 1):
    print(f"\nTEST CASE {i}: {test_name}")
    if result:
        successful_images = [img for img in result['generated_images'] if img['status'] == 'success']
        failed_images = [img for img in result['generated_images'] if img['status'] == 'failed']
        
        print(f"Characters with images: {len(successful_images)}")
        print(f"Failed generations: {len(failed_images)}")
        
        for img_info in successful_images:
            print(f"  {img_info['character']}: {img_info['image_file']}")
        
        if failed_images:
            for img_info in failed_images:
                print(f"  {img_info['character']}: Failed to generate")
    else:
        print(f"COMPLETE FAILURE")


print("Check your directory for generated image files")
