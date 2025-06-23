import functions_framework
import gspread
import google.auth
from google.cloud import pubsub_v1
from google.cloud import secretmanager
import os
import json

# --- CONFIGURATION ---
PROJECT_ID = os.environ.get('GCP_PROJECT', 'focused-sentry-463612-e1')
SHEET_ID = "YOUR_GOOGLE_SHEET_ID"  # Replace with your Google Sheet ID
SECRET_NAME = "gemini-api-key"

# --- CLIENT INITIALIZATION ---
# Initialize clients for Google Sheets
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
# When running on Cloud Run, it uses the attached service account's identity
credentials, project_id = google.auth.default(scopes=scopes)
gc = gspread.authorize(credentials)

# Get the API Key and configure the Gemini client
try:
    sm_client = secretmanager.ServiceClient()
    key_name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    response = sm_client.access_secret_version(request={"name": key_name})
    API_KEY = response.payload.data.decode("UTF-8")
    # This part is for validation, the actual client is in other agents
    if API_KEY:
        print("Successfully retrieved API Key for the system.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not retrieve API Key: {e}")
    API_KEY = None


def get_next_story_idea():
    """Finds the next story idea row with the status 'Chưa xử lý' (Not Processed)."""
    try:
        worksheet = gc.open_by_key(SHEET_ID).sheet1
        all_data = worksheet.get_all_records()
        for index, row in enumerate(all_data):
            if row.get("Trạng Thái") == "Chưa xử lý":
                # Return the row data and its index (index + 2 for 1-based index and header)
                return row, index + 2
        return None, None
    except Exception as e:
        print(f"Error reading Google Sheet: {e}")
        return None, None

def notify_illustrator_agent(story_text: str):
    """Publishes the generated story to the 'image_requests' topic to trigger the Illustrator Agent."""
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, "image_requests")
    data = story_text.encode("utf-8")
    try:
        future = publisher.publish(topic_path, data)
        print(f"Published story to 'image_requests' topic, message ID: {future.result()}")
    except Exception as e:
        print(f"Error publishing to Pub/Sub: {e}")


def update_status_in_sheet(row_index, status):
    """Updates the status column in the Google Sheet."""
    try:
        worksheet = gc.open_by_key(SHEET_ID).sheet1
        # Column G is the 7th column
        worksheet.update_cell(row_index, 7, status)
        print(f"Updated status for row {row_index} to '{status}'")
    except Exception as e:
        print(f"Error updating Google Sheet: {e}")


@functions_framework.http
def story_agent_handler(request):
    """The main handler for the Storyteller Agent, triggered by Cloud Scheduler."""
    print("Storyteller Agent starting...")

    idea_data, row_index = get_next_story_idea()

    if not idea_data:
        print("No new story ideas found. Stopping.")
        return "No new ideas found.", 200

    print(f"Processing idea from row: {row_index}")
    update_status_in_sheet(row_index, "Đang xử lý (Processing)")

    # For this agent, we assume the story is the combination of the fields
    # as the Gemini call was moved to the Illustrator Agent for prompt engineering.
    story = f"{idea_data.get('Nhân Vật Tham Gia')} {idea_data.get('Hoạt Động Chính')} {idea_data.get('Bối Cảnh / Địa Điểm')}. Bất ngờ, {idea_data.get('Tình Huống Bất Ngờ')}. Bài học là {idea_data.get('Cảm Xúc Chủ Đạo / Bài Học Nhỏ')}."
    print("--- STORY DRAFT CREATED ---")
    print(story)
    print("---------------------------")

    # TRIGGER THE SECOND AGENT
    notify_illustrator_agent(story)

    # Update to a new status
    update_status_in_sheet(row_index, "Đã yêu cầu vẽ tranh (Image Requested)")

    return f"Story created and image requested for row {row_index}.", 200