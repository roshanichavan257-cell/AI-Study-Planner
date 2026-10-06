import os
import requests
import markdown
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
def ask_ai(question, context="", raw=False):
    prompt = f"""
You are a helpful AI assistant similar to ChatGPT.

Answer ANY normal question asked by the user.

You can answer:
- General questions
- General knowledge
- Education
- Programming
- Python, Java, C, C++
- HTML, CSS, JavaScript
- Computer Networks
- Artificial Intelligence
- Machine Learning
- Mathematics
- Science
- Software Engineering
- Projects
- Exams and homework
- Study planning
- Career and technology questions
- Writing and explanations
- Any other appropriate question

RULES:
1. Answer the user's actual question directly.
2. Do not repeat the question.
3. Do not give unrelated information.
4. Keep the answer clear and useful.
5. If multiple questions are asked, answer ALL of them.
6. If code is requested, provide correct code and a short explanation.
7. Use headings and bullet points when useful.
8. Do not mention these instructions.

Student planner information:
{context}

User question:
{question}
"""

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.5-flash-lite:generateContent"
    )

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=60
        )

        result = response.json()

        # Quota / rate limit
        if response.status_code == 429:

            return """
            <div class="alert alert-warning">
                🤖 <b>AI is temporarily unavailable.</b><br><br>
                The free Gemini API limit has been reached.
                Please try again later.
            </div>
            """

        # Other API errors
        if response.status_code != 200:
            return f"""
            <div class="alert alert-danger">
            ❌ Gemini Error:<br><br>
            {result}
            </div>
            """

        # Get AI response
        ai_text = result["candidates"][0]["content"]["parts"][0]["text"]
        # Quiz साठी raw AI response return करा
        if raw:
            return ai_text
        # Normal chatbot साठी HTML return करा
        html_answer = markdown.markdown(
            ai_text,
            extensions=[
                "fenced_code",
                "tables"
            ]
        )
        return html_answer

    except requests.exceptions.Timeout:

        return """
        <div class="alert alert-warning">
            ⏳ AI took too long to respond.
            Please try again.
        </div>
        """

    except Exception as e:

        return """
        <div class="alert alert-danger">
            ❌ AI service is currently unavailable.
        </div>
        """