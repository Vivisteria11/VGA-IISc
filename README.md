Quick Start Guide
Follow these steps to get the project running.

1.First, clone the project repository to your local machine.

git clone <your-repository-url>
cd <your-project-folder>

2.Install all the required Python packages using the requirements.txt file.

pip install -r requirements.txt

3. Create a new file named .env in the main project folder and add your API key.

GEMINI_API_KEY="YOUR_API_KEY_HERE"

4.In your first terminal, start the Flask API server.

python flask_server.py

Leave this terminal running.

5.Open a new, second terminal and run the Streamlit application.

streamlit run streamlit_app.py

The application will open in your web browser. You can now follow the on-screen prompts to generate your story and scenes.
