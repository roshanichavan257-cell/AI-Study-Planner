import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def ask_ai(question, context=""):

    prompt = f"""
You are an AI Study Assistant.

Help the student with:
- Programming
- Python
- Java
- HTML
- CSS
- JavaScript
- Computer Networks
- Software Testing
- Artificial Intelligence
- Machine Learning
- Mathematics
- Exams
- Homework
- Study Planning
- General academic questions

Student's Study Planner information:
{context}

Student's question:
{question}

Give a clear, simple and useful answer.
If the user asks for code, provide the code and explain it.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return response.text