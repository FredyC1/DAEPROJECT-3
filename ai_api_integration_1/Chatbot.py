import requests
import json

CHAT_FILE = "Generated.json"
chat_messages = []

while True:
    user_question = input("You: ")
    if user_question.lower() in ["exit", "quit"]:
        break
    
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": "Bearer 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",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "model": "google/gemma-3-4b-it:free",
            "messages": [{"role": "user", "content": user_question}]
        })
    )
    
    data = response.json()
    reply = data["choices"][0]["message"]["content"]
    print("AI:", reply)
    
    # Append to history
    chat_messages.append({"role": "user", "content": user_question})
    chat_messages.append({"role": "assistant", "content": reply})
    
    # Save to file
    with open(CHAT_FILE, 'w') as f:
        json.dump({"messages": chat_messages}, f, indent=2)