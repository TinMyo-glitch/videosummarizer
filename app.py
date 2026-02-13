import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound
)
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# ==============================
# Gemini API Key Setup
# ==============================
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GENAI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in environment variables")

genai.configure(api_key=GENAI_API_KEY)


# ==============================
# Extract YouTube Video ID
# ==============================
def extract_video_id(url):
    if "youtu.be" in url:
        return url.split("/")[-1]
    elif "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return None


# ==============================
# Summarize API Route
# ==============================
@app.route('/summarize', methods=['POST'])
def summarize_video():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    video_url = data.get('url')
    style = data.get('style', 'Normal')

    if not video_url:
        return jsonify({"error": "Video URL is required"}), 400

    video_id = extract_video_id(video_url)

    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        # ==============================
        # 1. Get YouTube Transcript
        # ==============================
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join(
            [item['text'] for item in transcript_list]
        )

        if not transcript_text.strip():
            return jsonify({"error": "Transcript is empty"}), 400

        # ==============================
        # 2. Prepare Gemini Prompt
        # ==============================
        prompt = f"""
You are a helpful assistant.

Summarize the following YouTube video transcript in Burmese language.

Style: {style}

Transcript:
{transcript_text[:12000]}
"""

        # ==============================
        # 3. Generate Summary
        # ==============================
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        summary_text = response.text if response.text else "No summary generated."

        return jsonify({
            "summary": summary_text
        })

    # ✅ Specific Errors First
    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({
            "error": "No subtitles available for this video"
        }), 400

    # ✅ Generic Error Last
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# ==============================
# Run Server
# ==============================
if __name__ == '__main__':
    app.run(debug=True)
