import functions_framework
import base64
import json
import time
import os
from google.cloud import storage
import google.generativeai as genai
from google.cloud import secretmanager
from google.adk.agents import Agent

# --- CONFIGURATION ---
PROJECT_ID = os.environ.get('GCP_PROJECT', 'focused-sentry-463612-e1')
BUCKET_NAME = f"lucky-story-images-{PROJECT_ID}"
SECRET_NAME = "gemini-api-key"
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)
THEMES = {
    "default": "background-color: #f0f8ff; color: #333;",
    "sunset_forest": "background: linear-gradient(120deg, #ff7e5f, #feb47b); color: #ffffff; text-shadow: 1px 1px 2px #583101;",
    "calm_river": "background: linear-gradient(to right, #e0c3fc, #8ec5fc); color: #2c3e50;",
    "sunny_day": "background-color: #fffacd; color: #4682b4;"
}

# --- GLOBAL CLIENT INITIALIZATION ---
# This is the solution for the ValueError.
# The Gemini "brain" is initialized once when the Cloud Function instance starts.
GEMINI_MODEL_CLIENT = None
try:
    print("Initializing global Gemini brain...")
    sm_client = secretmanager.ServiceClient()
    key_name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    response = sm_client.access_secret_version(request={"name": key_name})
    api_key = response.payload.data.decode("UTF-8")
    genai.configure(api_key=api_key)
    GEMINI_MODEL_CLIENT = genai.GenerativeModel("gemini-1.5-flash-latest")
    print("GLOBAL: Agent's Gemini brain initialized successfully.")
except Exception as e:
    print(f"GLOBAL ERROR: Critical failure initializing agent's brain: {e}")

# --- WEB DESIGNER AGENT (ADK Version - Fixed) ---
class WebPublisherAgent(Agent):
    """
    An intelligent agent, using ADK, that "thinks" to choose a theme
    and "acts" to generate a webpage.
    """
    def __init__(self):
        # __init__ is now lightweight, no new attributes are added.
        super().__init__(name="WebPublisherAgent")
        print("WebPublisherAgent initialized.")

    def _think_what_theme_to_use(self, story_text: str) -> str:
        """'Think' phase: The agent analyzes the story and decides on a theme."""
        print("Agent is 'thinking' which theme to use...")
        if not GEMINI_MODEL_CLIENT:
            print("Brain is not available, selecting 'default' theme.")
            return "default"
        
        prompt = f"""
        Read the story's mood and choose the best theme name from this list: [sunset_forest, calm_river, sunny_day, default].
        Return only the chosen theme name.
        Story: "{story_text}"
        """
        try:
            response = GEMINI_MODEL_CLIENT.generate_content(prompt)
            theme = response.text.strip().replace("'", "").replace('"', '')
            final_theme = theme if theme in THEMES else "default"
            print(f"Agent decided on theme: '{final_theme}'")
            return final_theme
        except Exception as e:
            print(f"Agent 'thinking' process failed: {e}. Selecting 'default' theme.")
            return "default"

    def _act_to_build_webpage(self, story_text: str, image_gcs_path: str, theme_name: str):
        """'Act' phase: The agent builds and publishes the webpage."""
        print(f"Agent is 'acting': building webpage with theme '{theme_name}'...")
        # Convert GCS path (gs://...) to a public URL (https://...)
        image_public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{image_gcs_path.split('/')[-1]}"
        story_title = story_text.split('.')[0]
        story_file_name = f"stories/{int(time.time())}.html"
        selected_css = THEMES.get(theme_name, THEMES["default"])

        story_html_content = f"""
        <!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>{story_title}</title>
        <style>body {{ font-family: sans-serif; margin: 40px; transition: background-color 0.5s; {selected_css} }} .container {{ max-width: 800px; margin: auto; background-color: rgba(255,255,255,0.85); padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }} img {{ max-width: 100%; border-radius: 8px; }}</style>
        </head><body><div class="container"><h1>{story_title}</h1><p><a href="../index.html">Back to Home</a></p>
        <img src="{image_public_url}" alt="{story_title}"><p style="white-space: pre-wrap;">{story_text}</p></div></body></html>
        """
        
        # Upload the detailed story page to GCS
        story_blob = bucket.blob(story_file_name)
        story_blob.upload_from_string(story_html_content, content_type="text/html; charset=utf-8")
        
        # Update the index.html file
        index_blob = bucket.blob("index.html")
        try:
            current_index_content = index_blob.download_as_text()
        except Exception:
            current_index_content = """
            <!DOCTYPE html><html lang="vi"><head><title>The Adventures of Lucky</title>
            <style>body {{ font-family: sans-serif; margin: 40px; background-color: #eee; }} ul {{ list-style-type: none; padding: 0; }} li {{ background: white; margin: 5px 0; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}</style></head>
            <body><h1>The Adventures of Lucky</h1><ul></ul></body></html>
            """
        new_link = f'<li><a href="{story_file_name}">{story_title} (Date: {time.strftime("%Y-%m-%d")})</a></li>'
        updated_index_content = current_index_content.replace("<ul>", f"<ul>\n{new_link}")
        index_blob.upload_from_string(updated_index_content, content_type="text/html; charset=utf-8")
        print("Agent has completed the 'act' of publishing the webpage.")

    def run(self, story_text: str, image_gcs_path: str):
        """The main agent loop: Think -> Act."""
        theme = self._think_what_theme_to_use(story_text)
        self._act_to_build_webpage(story_text, image_gcs_path, theme)

# --- TRIGGER FUNCTION ---
@functions_framework.cloud_event
def web_agent_handler(cloud_event):
    """The trigger function, which initializes and runs the Agent."""
    message_data_str = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    message_data = json.loads(message_data_str)
    
    story_text = message_data.get("story_text")
    image_gcs_path = message_data.get("image_gcs_path")
    
    if story_text and image_gcs_path:
        # Initialize and run the agent
        agent = WebPublisherAgent()
        agent.run(story_text, image_gcs_path)
    else:
        print("Error: Incomplete data received.")
        
    return "OK", 200