from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime
from fuzzywuzzy import fuzz
from langdetect import detect
from deep_translator import GoogleTranslator
import requests

app = Flask(__name__)

 ===== Load Dataset =====
with open("imam_zamana_chatbot_dataset.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

# ===== Groq API Key from Environment Variable =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Stored in Render environment

if not GROQ_API_KEY:
    raise ValueError("🚨 Missing GROQ_API_KEY environment variable!")

# ===== Language Detection =====
def detect_language(text):
    try:
        lang = detect(text)
        if all(ord(c) < 128 for c in text):
            return "English"
        if lang == "hi":
            return "Hindi"
        elif any(w in text.lower() for w in ["kya", "hai", "kaun", "kab", "kyunki", "ke", "ki", "wo", "unka", "unke"]):
            return "Hinglish"
        return "English"
    except:
        return "English"

# ===== Translation =====
def translate_to_english(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except:
        return text

def translate_back(text, lang):
    if lang == "English":
        return text
    try:
        target = "hi" if lang in ["Hindi", "Hinglish"] else "en"
        return GoogleTranslator(source='en', target=target).translate(text)
    except:
        return text

# ===== Dataset Search =====
def get_dataset_answer(translated_q, lang_field, threshold=70):
    best_score, best_answer = 0, None
    for item in dataset:
        score = fuzz.ratio(translated_q.lower(), item["question"].lower())
        if score > best_score and score >= threshold:
            best_score = score
            best_answer = item.get(lang_field)
    return best_answer

# ===== Topic Check =====
def is_about_mahdi(text):
    text = text.lower().strip()

    keywords = [
        "imam", "mahdi", "mehdi", "imam mahdi", "imam mehdi",
        "imam e zamana", "imam zaman", "hazrat mahdi", "313",
        "zuhur", "zahoor", "ghaibat", "rajat", "ajtf", "a.s",
        "al mahdi", "hidden imam", "imam of time", "qaem", "qaim",
        "sahib uz zaman", "imam asr", "imam hujjat", "imam askari"
    ]

    return any(k in text for k in keywords)
# ===== Groq API Call =====
def ask_groq(question):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [
        {"role": "system", "content": "You are a helpful Shia Islamic assistant. Only answer questions about Imam Mahdi (a.s.) accurately and briefly."},
        {"role": "user", "content": question}
    ]
    payload = {
        "model": "llama3-8b-8192",
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 400
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"❌ Groq Error: {str(e)}"

# ===== Response Generator =====
def get_response(user_input):
    user_lang = detect_language(user_input)
    translated_q = translate_to_english(user_input) if user_lang != "English" else user_input
    lang_field = "answer_hi" if user_lang in ["Hindi", "Hinglish"] else "answer_en"

    if is_about_mahdi(translated_q):
        answer = get_dataset_answer(translated_q, lang_field)
        source = "📘 From Najaf Jafri.313" if answer else "🌐 Najaf Jafri.313"
        if not answer:
            answer = ask_groq(translated_q)
    else:
        answer = "यह चैटबॉट केवल इमाम महदी (a.s.) से संबंधित सवालों का जवाब देता है।"
        source = "⚠️ Restricted Mode"

    final_answer = translate_back(answer, user_lang)
    return final_answer, source, user_lang

# ===== Flask Routes =====
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get", methods=["POST"])
def chatbot_response():
    user_input = request.json.get("message")
    reply, source, lang = get_response(user_input)
    return jsonify({"reply": reply, "source": source, "lang": lang, "time": datetime.now().strftime("%I:%M %p")})

if __name__ == "__main__":
    app.run(debug=True)
