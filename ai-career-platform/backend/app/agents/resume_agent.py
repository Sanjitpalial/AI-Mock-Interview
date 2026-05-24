from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.messages import (
    HumanMessage,
    SystemMessage
)

import json

from app.config import settings

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0
)

RESUME_ANALYSIS_PROMPT = """
You are an expert resume analyzer.

Analyze the resume and return ONLY valid JSON:

{
  "skills": [],
  "experience": "",
  "role": "",
  "projects": [],
  "strengths": [],
  "gaps": []
}
"""

async def analyze_resume(
    resume_text: str
):

    messages = [

        SystemMessage(
            content=RESUME_ANALYSIS_PROMPT
        ),

        HumanMessage(
            content=f"Resume:\n{resume_text}"
        )
    ]

    response = await llm.ainvoke(messages)

    try:
        return json.loads(response.content)

    except:

        return {
            "skills": [],
            "experience": "Intermediate",
            "role": "Software Engineer",
            "projects": [],
            "strengths": [],
            "gaps": []
        }