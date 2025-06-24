# Lucky's Dream Weaver: An AI Storytelling Engine

![Google Cloud](https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Hackathon](https://img.shields.io/badge/Hackathon-Project-brightgreen?style=for-the-badge)

An autonomous multi-agent AI system built for the `Agent Development Kit Hackathon with Google Cloud`. This project automates the entire creative pipeline, from idea to a fully illustrated, custom-designed webpage, telling the daily adventures of Lucky the puppy.

---

## 🚀 Live Demo

**[View the Live Website Here](https://storage.googleapis.com/lucky-story-images-focused-sentry-463612-e1/index.html)**

*Note: A new story is generated automatically every day at 7 AM (GMT+7). You can also manually trigger a new story generation by following the "How to Test" guide below.*

## ✨ Core Features

* **Fully Autonomous Content Pipeline:** A single daily trigger initiates an end-to-end workflow that requires zero human intervention.
* **Multi-Agent Architecture:** The system is composed of three distinct, specialized agents that collaborate asynchronously using a Pub/Sub messaging backbone.
* **AI-Powered Creativity:** Leverages Gemini for creative writing and prompt engineering, and Imagen for generating unique, high-quality illustrations.
* **Intelligent, Dynamic Web Design:** The final agent acts as an AI Web Designer, perceiving the story's mood to autonomously decide on a unique visual theme (colors, background, effects) for each published page.
* **Serverless & Event-Driven:** Built entirely on scalable, serverless Google Cloud services for efficiency and reliability.

## 🏛️ Architecture: A Symphony of Agents

The entire system is an event-driven assembly line for creativity. Each agent performs its task and then passes the artifact to the next agent via Cloud Pub/Sub, ensuring the system is decoupled and resilient.

```
(START)
   |
[ Cloud Scheduler ] --(1. HTTP Trigger)--> [ Agent 1: Storyteller ] --(2. Reads/Writes)--> [ Google Sheets ]
                                                  |
                                                  V (3. Publishes story)
                                       [ Pub/Sub Topic: 'image_requests' ]
                                                  |
                                                  V (4. Event Trigger)
                                       [ Agent 2: Illustrator ] --------------------------------------------+
                                                  |                                                           |
                                                  +--(5a. Uses Gemini for prompt via)--> [ Google AI API ]   |
                                                  |    (w/ key from Secret Manager)                         |
                                                  |                                                           |
                                                  +--(5b. Uses Imagen for image via)--> [ Vertex AI ]         |
                                                  |                                                           |
                                                  V (6. Saves image to)                                     |
                                       [ Google Cloud Storage ] <-------------------------------------------+ (8b. Saves HTML to)
                                                  |
                                                  V (7. Publishes story + image path)
                                       [ Pub/Sub Topic: 'publishing_requests' ]
                                                  |
                                                  V (8. Event Trigger)
                                       [ Agent 3: Web Publisher (ADK) ]
                                                  |
                                                  +--(8a. Uses Gemini for theme via)--> [ Google AI API ]
                                                  |
                                                  V
                                           (Updates Website)
                                                  |
                                                  V
[ End User ] <---(9. Browses Website)--- [ GCS Static Website ]
                                                  |
                                                (END)
```
## 🛠️ Tech Stack

### Languages, Frameworks & Libraries

  * **Python:** The primary language for all backend agents.
  * **Google Agent Development Kit (`google-adk`):** The core framework for structuring our final intelligent agent.
  * **Functions Framework:** To wrap our Python code for deployment on Cloud Run.
  * **AI Libraries:** `google-generativeai` (for Gemini) and `google-cloud-aiplatform` (for Imagen).
  * **Google Cloud Client Libraries:** `google-cloud-storage`, `google-cloud-pubsub`, `google-cloud-secret-manager`.
  * **Other Tools:** `gspread` for Google Sheets integration.

### Platforms, Tools & Cloud Services

  * **Compute:** **Google Cloud Run** for serverless, containerized agent hosting.
  * **AI/ML:** **Vertex AI (Imagen)** and the **Google AI API (Gemini)**.
  * **Storage:** **Google Cloud Storage** (for asset storage and static website hosting) and **Artifact Registry** (for Docker image storage).
  * **Messaging:** **Cloud Pub/Sub** for asynchronous, event-driven communication between agents.
  * **Automation & Security:** **Cloud Scheduler** for daily triggers, **IAM** for service account management, and **Secret Manager** for API key security.
  * **Deployment:** **Docker**, **Cloud Build**, and the **gcloud CLI**.

## 👤 Author

  * **Anh-Dnt** - [https://github.com/Anh-Dnt](https://www.google.com/search?q=https://github.com/Anh-Dnt)

## 📄 License

This project is licensed under the MIT License.
