# Bullet: Story Analyzer 🎬

This system provides a fast, asynchronous web service that analyzes narrative scripts. It evaluates emotional arcs, estimates reader engagement, summarizes the plot, and provides actionable storytelling improvements.

## 1. Overall Approach

The core design principle revolves around speed, modularity, and fault tolerance:
* **Parallel Processing:** Instead of waiting for one LLM call to finish before starting the next, the system uses `asyncio.gather` to run all four analysis engines (Summary, Emotion, Engagement, Recommendations) simultaneously.
* **Defensive Fallbacks:** If an LLM fails, truncates output, or drops array items, it doesn't crash the API. The system catches the error, dynamically pads missing data, and returns a safe fallback for that specific module to ensure the frontend always renders.
* **Lightweight Frontend:** The dashboard avoids heavy charting libraries (like Chart.js). Instead, it uses the native HTML5 Canvas API to draw custom, responsive charts instantly.

## 2. Zero-Hallucination Structured Outputs

The application has been heavily refactored to utilize **Native Structured Outputs** rather than relying on prompt engineering and manual JSON parsing.
* **Pydantic Driven:** Every engine (Emotion, Engagement, etc.) defines its exact expected schema using `Pydantic v2`. The LLMs are forced to adhere strictly to these models, completely eliminating structure hallucinations.
* **Dynamic Context-Awareness:** Instead of forcing hardcoded UI metrics, the `Engagement` engine now generates dynamic factors (e.g., `mystery_hook`, `comedic_timing`) based on the script's specific genre.
* **Custom Gemini Schema Parser:** While OpenAI natively supports strict JSON schemas, Google Gemini strictly rejects schemas with `$ref`, `$defs`, and `anyOf`. This project includes a custom schema parser (`_to_gemini_schema`) that flattens Pydantic outputs and translates them into Gemini-compliant OpenAPI schemas on the fly, unlocking cross-provider compatibility.

## 3. Tools & Technologies Used

* **Backend:** `FastAPI` (for async routing) and `Pydantic v2` (for strict data validation and Schema generation).
* **Frontend:** Vanilla HTML/CSS and JavaScript (App.js). No React or heavy bundles. Adaptive UI capable of rendering dynamic API factors.
* **Caching:** `Redis` is used to cache identical script payloads (using SHA-256 hashes) to save LLM API costs and reduce latency.
* **LLMs:** * Default support for `gpt-4o-mini` (via OpenRouter/OpenAI) and `gemini-2.0-flash` (via Google AI Studio).
  * Includes a built-in `Mock` provider for fast local UI testing without requiring API keys.

## 4. Limitations of the Current System

* **Exact-Match Caching:** The Redis cache relies on an exact string hash. If a user adds a single space or fixes a typo in an identical script, it will miss the cache and trigger a full API request.
* **Model Truncation:** Highly constrained open-source models (e.g., through proxy routers) might truncate nested arrays if token limits are hit, relying heavily on the backend's padding mechanisms.
* **Basic Text Parsing:** The script normalizer relies on regex patterns (e.g., looking for "Title:" or "Dialogue:"). Unconventional formatting might not parse optimally.

## 5. Possible Future Improvements

1. **Semantic Caching:** Replace the exact-match Redis cache with a Vector Database (like Weaviate) so that semantically similar scripts hit the cache, saving resources on minor edits.
2. **Server-Sent Events (SSE):** Refactor the API to stream results to the frontend. This would allow individual dashboard widgets (like Summary or Engagement gauges) to light up immediately as their specific engine finishes.
3. **Long-Form Script Support:** Implement a chunking and map-reduce architecture to allow the analysis of full 120-page screenplays rather than just single scenes.

## 🚀 Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
2. Set up your environment variables (in a .env file):
   ```bash
   OPENAI_API_KEY=your_key_here
   GEMINI_API_KEY=your_key_here
   ANALYSIS_MODE=live
3. Run the server:
   ```bash
   uvicorn main:app --reload
   Open your browser and navigate to http://localhost:8000.
