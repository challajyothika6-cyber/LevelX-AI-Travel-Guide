from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
import requests
import tempfile
import base64
import os


app = Flask(__name__)
CORS(app)

MURF_API_KEY = "API_KEY"
GEMINI_API_KEY = "API_KEY"



client = genai.Client(api_key=GEMINI_API_KEY)



PROMPTS = {

    "Summary": """
You are a professional tourist guide.

Provide a high-level overview of "{place}" in {language}.

Focus on:
- The historical significance
- Why the place is famous
- Key architectural or cultural highlights

Keep the explanation concise, engaging, and easy to follow.
Avoid excessive details and dates.
Limit the response to around 200 words.

Respond ONLY in {language}.
""",

    "Detailed": """
You are a professional tourist guide.

Provide a detailed and immersive explanation of "{place}" in {language}.

Cover:
- Historical background and timeline
- Architectural design and unique features
- Cultural importance and notable events
- Interesting facts and visitor insights

Explain concepts clearly and in a storytelling manner.
Include relevant details and examples to create a rich experience.

Limit the response to around 400 words.

Respond ONLY in {language}.
"""
}



def generate_description(place, answer_type, language):

    if answer_type not in PROMPTS:
        raise ValueError(
            "Invalid answerType. Use Summary or Detailed."
        )

    prompt = PROMPTS[answer_type].format(
        place=place,
        language=language
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    if not response or not response.text:
        raise Exception("Gemini did not return any text.")

    return response.text.strip()



def generate_speech(text, voice_id, locale):

    url = "https://global.api.murf.ai/v1/speech/stream"

    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "voice_id": voice_id,
        "text": text,
        "locale": locale,
        "model": "FALCON",
        "format": "MP3",
        "sampleRate": 24000,
        "channelType": "MONO"
    }

    print("Sending request to Murf...")

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=120
    )

    if response.status_code != 200:
        raise Exception(
            f"Murf API Error {response.status_code}: "
            f"{response.text}"
        )

    temp_audio = tempfile.NamedTemporaryFile(
        suffix=".mp3",
        delete=False
    )

    audio_path = temp_audio.name
    temp_audio.close()

    try:

        with open(audio_path, "wb") as audio_file:

            for chunk in response.iter_content(
                chunk_size=1024
            ):
                if chunk:
                    audio_file.write(chunk)

        print("Audio generated successfully.")

        return audio_path

    except Exception:

        if os.path.exists(audio_path):
            os.remove(audio_path)

        raise



@app.route("/generate-audio-guide", methods=["POST"])
def generate_audio_guide():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "error": "Request body is empty"
            }), 400


        

        place = data.get("place")
        answer_type = data.get("answerType")
        language = data.get("language")
        voice_id = data.get("voiceId")
        locale = data.get("locale")


        
        missing_fields = []

        if not place:
            missing_fields.append("place")

        if not answer_type:
            missing_fields.append("answerType")

        if not language:
            missing_fields.append("language")

        if not voice_id:
            missing_fields.append("voiceId")

        if not locale:
            missing_fields.append("locale")


        if missing_fields:

            return jsonify({
                "error": "Missing required fields",
                "fields": missing_fields
            }), 400


        
        print("--------------------------------")
        print("Generating description...")
        print("Place:", place)
        print("Type:", answer_type)
        print("Language:", language)

        text_description = generate_description(
            place,
            answer_type,
            language
        )

        print("Description generated.")


        
        print("Generating audio...")

        audio_path = generate_speech(
            text_description,
            voice_id,
            locale
        )


        
        with open(audio_path, "rb") as audio_file:
            audio_bytes = audio_file.read()


        
        encoded_audio = base64.b64encode(
            audio_bytes
        ).decode("utf-8")


        
        if os.path.exists(audio_path):
            os.remove(audio_path)


        
        print("Everything completed successfully.")

        return jsonify({
            "description": text_description,
            "audioBase64": encoded_audio
        })


    except Exception as e:

        print("--------------------------------")
        print("ERROR:", str(e))
        print("--------------------------------")

        return jsonify({
            "error": str(e)
        }), 500



@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "message": "Travel Guide Backend is running",
        "status": "OK"
    })



if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )