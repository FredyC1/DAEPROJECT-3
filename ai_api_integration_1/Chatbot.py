import os
import requests
import json
from dotenv import load_dotenv

# ── Load API key from .env (never hardcode secrets in source!
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise EnvironmentError(
        "OPENROUTER_API_KEY not found. "
        "Create a .env file with: OPENROUTER_API_KEY=your_key_here"
    )

BASE_URL  = "https://openrouter.ai/api/v1"
MODEL     = "google/gemma-3-4b-it:free"
CHAT_FILE = "Generated.json"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

chat_messages = []

# ── Weather keywords used to detect weather-related questions
WEATHER_KEYWORDS = [
    "weather", "temperature", "forecast", "rain", "sunny",
    "cloudy", "wind", "humidity", "snow", "hot", "cold"
]



# API #1 – OpenRouter (AI Chat)


def fetch_models() -> list[str]:
    """
    GET /models
    REST type: GET
    Purpose:   Retrieve list of available free AI models from OpenRouter.
    Status codes handled: 200, 401, 429, 500, and network errors.
    """
    try:
        response = requests.get(f"{BASE_URL}/models", headers=HEADERS, timeout=10)

        # ── Status-code validation ────────────────────────────────────────
        if response.status_code == 200:
            models_data = response.json().get("data", [])
            return [m["id"] for m in models_data if ":free" in m.get("id", "")]

        elif response.status_code == 401:
            print("[Error] 401 Unauthorized – your API key is invalid.")
        elif response.status_code == 429:
            print("[Error] 429 Too Many Requests – rate limit reached.")
        elif response.status_code == 500:
            print("[Error] 500 Server Error – OpenRouter is down.")
        else:
            print(f"[Error] Unexpected status {response.status_code} while fetching models.")

    except requests.exceptions.ConnectionError:
        print("[Warning] Could not reach OpenRouter – check your internet connection.")
    except requests.exceptions.Timeout:
        print("[Warning] Model list request timed out.")
    except (KeyError, ValueError) as e:
        print(f"[Warning] Unexpected response format when fetching models: {e}")

    return []


def send_message(messages: list[dict]) -> str | None:
    """
    POST /chat/completions
    REST type: POST
    Purpose:   Send conversation history and receive an AI reply.
    Status codes handled: 200, 401, 429, 500, and network errors.
    """
    payload = {
        "model": MODEL,
        "messages": messages,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=HEADERS,
            data=json.dumps(payload),
            timeout=30,
        )

        # ── Status-code validation ────────────────────────────────────────
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]

        elif response.status_code == 401:
            print("[Error] 401 Unauthorized – your API key is invalid or missing.")
        elif response.status_code == 429:
            print("[Error] 429 Too Many Requests – you've hit the rate limit. Wait a moment.")
        elif response.status_code == 500:
            print("[Error] 500 Server Error – OpenRouter is having issues. Try again later.")
        else:
            print(f"[Error] Unexpected status {response.status_code}: {response.text[:200]}")

    except requests.exceptions.ConnectionError:
        print("[Error] No internet connection – could not reach OpenRouter.")
    except requests.exceptions.Timeout:
        print("[Error] Request timed out – the server took too long to respond.")
    except (KeyError, IndexError, ValueError) as e:
        print(f"[Error] Could not parse AI response: {e}")

    return None


# API #2 – wttr.in (Weather)


def fetch_weather(city: str) -> str | None:
    """
    GET wttr.in/{city}?format=j1
    REST type: GET
    Purpose:   Retrieve current weather data for a city (no API key required).
    Status codes handled: 200, 404, 500, and network errors.

    Returns a plain-English summary string, or None on failure.
    """
    url = f"https://wttr.in/{city}?format=j1"

    try:
        response = requests.get(url, timeout=10)

        # ── Status-code validation ────────────────────────────────────────
        if response.status_code == 200:
            data = response.json()
            current = data["current_condition"][0]

            temp_c      = current["temp_C"]
            feels_like  = current["FeelsLikeC"]
            humidity    = current["humidity"]
            description = current["weatherDesc"][0]["value"]
            wind_kmph   = current["windspeedKmph"]

            return (
                f"Current weather in {city.title()}: {description}, "
                f"{temp_c}°C (feels like {feels_like}°C), "
                f"humidity {humidity}%, wind {wind_kmph} km/h."
            )

        elif response.status_code == 404:
            print(f"[Weather] 404 – City '{city}' not found. Try a different spelling.")
        elif response.status_code == 500:
            print("[Weather] 500 – Weather service is currently unavailable.")
        else:
            print(f"[Weather] Unexpected status {response.status_code} from weather API.")

    except requests.exceptions.ConnectionError:
        print("[Weather Error] Could not reach weather service – check your internet connection.")
    except requests.exceptions.Timeout:
        print("[Weather Error] Weather request timed out.")
    except (KeyError, IndexError, ValueError) as e:
        print(f"[Weather Error] Could not parse weather data: {e}")

    return None


def extract_city(question: str) -> str | None:
    """
    Simple heuristic to pull a city name from a weather question.
    Looks for the word after 'in', 'for', or 'at'.
    Example: "What's the weather in Miami?" → "Miami"
    """
    words = question.lower().split()
    triggers = {"in", "for", "at"}
    for i, word in enumerate(words):
        if word in triggers and i + 1 < len(words):
            return words[i + 1].strip("?!.,")
    return None


def is_weather_question(question: str) -> bool:
    """Returns True if the question appears to be about weather."""
    lower = question.lower()
    return any(keyword in lower for keyword in WEATHER_KEYWORDS)



def save_history(messages: list[dict]) -> None:
    """Write conversation history to JSON file."""
    try:
        with open(CHAT_FILE, "w") as f:
            json.dump({"messages": messages}, f, indent=2)
    except OSError as e:
        print(f"[Warning] Could not save chat history: {e}")



# Main chat loop


def main() -> None:
    print("=" * 55)
    print("  AI Chatbot  –  type 'exit' or 'quit' to stop")
    print("  Ask about weather: 'What's the weather in Tokyo?'")
    print("=" * 55)

    # Fetch available free models on startup (GET request)
    print("\nFetching available free models…")
    free_models = fetch_models()
    if free_models:
        print(f"Found {len(free_models)} free model(s). Using: {MODEL}\n")
    else:
        print(f"Could not retrieve model list. Proceeding with: {MODEL}\n")

    while True:
        user_question = input("You: ").strip()

        if not user_question:
            continue
        if user_question.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        # ── Weather injection: if weather question, fetch real data first ──
        messages_to_send = list(chat_messages)  # copy current history

        if is_weather_question(user_question):
            city = extract_city(user_question)
            if city:
                print(f"[Fetching weather for '{city}'…]")
                weather_info = fetch_weather(city)
                if weather_info:
                    # Inject weather data as context so the AI can use it
                    injected = (
                        f"[Live weather data] {weather_info} "
                        f"Use this to answer the user's question: {user_question}"
                    )
                    messages_to_send.append({"role": "user", "content": injected})
                else:
                    messages_to_send.append({"role": "user", "content": user_question})
            else:
                print("[Tip] For live weather, include a city: 'weather in London'")
                messages_to_send.append({"role": "user", "content": user_question})
        else:
            messages_to_send.append({"role": "user", "content": user_question})

        # ── Send to AI ─────────────────────────────────────────────────────
        reply = send_message(messages_to_send)

        if reply:
            print(f"AI: {reply}\n")
            # Save user's original question (not the injected one) to history
            chat_messages.append({"role": "user", "content": user_question})
            chat_messages.append({"role": "assistant", "content": reply})
            save_history(chat_messages)
        else:
            print("[Skipped] No reply received – your message was not saved.\n")


if __name__ == "__main__":
    main()