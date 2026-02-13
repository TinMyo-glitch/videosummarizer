import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

app = Flask(__name__)
CORS(app)  # Sketchware ကနေ လှမ်းခေါ်ရင် Error မတက်အောင်ပါ

# Render ရဲ့ Environment Variable မှာ GEMINI_API_KEY ထည့်ထားရပါမယ်
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)

def extract_video_id(url):
    # Youtube Link ပုံစံအမျိုးမျိုးကနေ ID ကို ဆွဲထုတ်ခြင်း
    if "youtu.be" in url:
        return url.split("/")[-1]
    elif "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return None

@app.route('/summarize', methods=['POST'])
def summarize_video():
    data = request.json
    video_url = data.get('url')
    style = data.get('style', 'Normal') # Default က Normal ပါ

    if not video_url:
        return jsonify({"error": "Video URL is required"}), 400

    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({"error": "Invalid Youtube URL"}), 400

    try:
        # 1. Youtube Video စာသားများကို ဆွဲထုတ်ခြင်း
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([i['text'] for i in transcript_list])

        # 2. Gemini ကို ပို့မည့် Prompt ပြင်ဆင်ခြင်း
        prompt = f"""
        You are a helpful assistant. Summarize the following YouTube video transcript in Burmese (Myanmar Language).
        Style: {style}
        
        Transcript:
        {transcript_text[:10000]} 
        (Note: Taking first 10000 chars to avoid token limits for demo)
        """

        # 3. Gemini ဖြင့် အဖြေထုတ်ခြင်း
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        return jsonify({"summary": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
