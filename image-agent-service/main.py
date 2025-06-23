import functions_framework
import base64
import os
import time
import json

# --- Imports for both worlds ---
# 1. For Vertex AI (for image generation)
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
# 2. For Google AI (for prompt generation)
import google.generativeai as genai
from google.cloud import secretmanager
from google.cloud import storage
from google.cloud import pubsub_v1

# --- CONFIGURATION ---
PROJECT_ID = os.environ.get('GCP_PROJECT', 'focused-sentry-463612-e1')
LOCATION = "asia-southeast1"
SECRET_NAME = "gemini-api-key"
BUCKET_NAME = f"lucky-story-images-{PROJECT_ID}" 

# --- CLIENT INITIALIZATION ---
# This operation automatically authenticates using the Cloud Run Service Account
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Function to get API Key from Secret Manager
def get_api_key_from_secret_manager():
    try:
        client = secretmanager.ServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"CRITICAL ERROR: Could not retrieve API Key from Secret Manager: {e}")
        return None

# Get the API Key and configure the Gemini client
API_KEY = get_api_key_from_secret_manager()
if API_KEY:
    genai.configure(api_key=API_KEY)

def generate_image_prompt_with_gemini(story_text: str) -> str:
    """Uses Google AI (API Key) to generate a detailed prompt for the image model."""
    print("Using Google AI (API Key) to generate an image prompt...")
    if not API_KEY:
        return "A cute white puppy named Lucky in a beautiful, gentle forest. Children's book illustration style."

    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    
    instructional_prompt = f"""
    Based on the children's story below, create a detailed, descriptive image generation prompt in English.
    Style Guidelines: Art Style: "gentle digital painting", "children's book illustration". Color Palette: "soft and gentle colors", "prioritize light blues, pastel greens". Details: "sharp and clear details", "expressive and cute characters".
    Story: "{story_text}"
    """
    try:
        response = model.generate_content(instructional_prompt)
        image_prompt = response.text
        print(f"Image prompt created (using Google AI): {image_prompt}")
        return image_prompt
    except Exception as e:
        print(f"Error generating prompt with Google AI: {e}")
        return f"A cute white puppy named Lucky in a beautiful, gentle forest. Children's book illustration style."

def generate_image_with_imagen(prompt: str):
    """Uses Vertex AI (Service Account) to generate the image from a prompt."""
    print(f"Using Vertex AI Imagen to generate image...")
    generation_model = ImageGenerationModel.from_pretrained("imagegeneration@006")
    try:
        response = generation_model.generate_images(prompt=prompt, number_of_images=1, aspect_ratio="1:1", quality=9)
        image_data_base64 = response.images[0]._image_bytes
        print("Successfully generated image using Vertex AI Imagen!")
        return image_data_base64
    except Exception as e:
        print(f"Error generating image with Imagen: {e}")
        return None

def save_image_to_gcs(image_bytes: bytes) -> str:
    """Saves the image file to Google Cloud Storage and returns its GCS URI."""
    if not image_bytes:
        print("No image data to save.")
        return None
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    
    # Create a unique filename using a timestamp
    timestamp = int(time.time())
    file_name = f"lucky-story-{timestamp}.png"
    
    blob = bucket.blob(file_name)
    try:
        blob.upload_from_string(image_bytes, content_type="image/png")
        gcs_uri = f"gs://{BUCKET_NAME}/{file_name}"
        print(f"Successfully saved image to GCS: {gcs_uri}")
        return gcs_uri
    except Exception as e:
        print(f"Error saving image to GCS: {e}")
        return None

def notify_web_agent(story_text: str, image_gcs_path: str):
    """Notifies the Web Agent that a new product is ready."""
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, "publishing-requests")
    message_data = {"story_text": story_text, "image_gcs_path": image_gcs_path}
    data = json.dumps(message_data).encode("utf-8")
    try:
        future = publisher.publish(topic_path, data)
        print(f"Published request to 'publishing-requests' topic, message ID: {future.result()}")
    except Exception as e:
        print(f"Error publishing to 'publishing-requests' topic: {e}")

@functions_framework.cloud_event
def image_agent_handler(cloud_event):
    """The main handler for the Illustrator Agent (Hybrid version), triggered by Pub/Sub."""
    story_text = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
    print("--- ILLUSTRATOR AGENT (HYBRID) RECEIVED REQUEST ---")
    
    detailed_prompt = generate_image_prompt_with_gemini(story_text)
    image_bytes = generate_image_with_imagen(detailed_prompt)
    
    if image_bytes:
        image_gcs_path = save_image_to_gcs(image_bytes)
        if image_gcs_path:
            print(f"Process complete. Image saved at: {image_gcs_path}")
            # TRIGGER THE FINAL AGENT
            notify_web_agent(story_text, image_gcs_path)
    else:
        print("Image generation process failed.")
        
    return "OK", 200