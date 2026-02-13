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
# Gemini Setup
# ==============================
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GENAI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set")

genai.configure(api_key=GENAI_API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

# ==============================
# Extract Video ID
# ==============================
def extract_video_id(url):
    if "youtu.be" in url:
        return url.split("/")[-1]
    elif "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return None


# ==============================
# Chunk Large Text
# ==============================
def chunk_text(text, chunk_size=10000):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


# ==============================
# Smart Prompt Builder
# ==============================
def build_prompt(transcript, style, length, language, bullet):

    bullet_instruction = "Use bullet points." if bullet else "Write in paragraph form."

    return f"""
You are a professional YouTube video summarizer AI.

Language: {language}
Summary Length: {length}
Style: {style}
{bullet_instruction}

Tasks:
1. Generate an engaging title.
2. Provide a clear summary.
3. Extract key important points.

Transcript:
{transcript}
"""


# ==============================
# Main API
# ==============================
@app.route('/summarize', methods=['POST'])
def summarize_video():

    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    video_url = data.get("url")
    style = data.get("style", "Normal")
    length = data.get("length", "Short")
    language = data.get("language", "Burmese")
    bullet = data.get("bullet", False)

    if not video_url:
        return jsonify({"error": "Video URL required"}), 400

    video_id = extract_video_id(video_url)

    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        # Get transcript
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join(
            [item["text"] for item in transcript_data]
        )

        if not transcript_text.strip():
            return jsonify({"error": "Empty transcript"}), 400

        # Handle long videos
        chunks = chunk_text(transcript_text, 10000)
        partial_summaries = []

        for chunk in chunks:
            prompt = build_prompt(chunk, style, length, language, bullet)
            response = model.generate_content(prompt)
            partial_summaries.append(response.text)

        # Merge summaries if multiple chunks
        if len(partial_summaries) > 1:
            merge_prompt = f"""
Combine and refine the following summaries into one final professional summary:

{''.join(partial_summaries)}
"""
            final_response = model.generate_content(merge_prompt)
            final_summary = final_response.text
        else:
            final_summary = partial_summaries[0]

        return jsonify({
            "summary": final_summary
        })

    except (TranscriptsDisabled, NoTranscriptFound):
        return jsonify({
            "error": "No subtitles available for this video"
        }), 400

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
