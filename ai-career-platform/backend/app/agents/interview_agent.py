from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from typing import TypedDict, List, Optional

from app.services.gemini import invoke_with_model_fallback
from app.agents.llm_utils import message_text


class InterviewState(TypedDict):
    resume_text: str
    role: str
    question_history: List[dict]
    current_question: Optional[str]
    question_count: int
    max_questions: int


def generate_question(state: InterviewState) -> InterviewState:
    history_str = "\n".join([
        f"Q: {q['question']}\nA: {q.get('answer', 'Not answered')}"
        for q in state["question_history"]
    ])

    prompt = f"""
You are conducting an interview tailored to: {state['role']}.
Resume summary: {state['resume_text'][:2000]}

Previous Q&A:
{history_str}

Generate the next interview question.
- Early questions: core technical for the role
- Middle: project-based or situational
- Later: follow-up or deeper dive

Return ONLY the question text. No numbering, no prefix.
"""
    response, _ = invoke_with_model_fallback(
        [HumanMessage(content=prompt)],
        temperature=0.7,
    )
    text = message_text(response)
    if not text:
        text = "Tell me about a recent project you worked on and your specific contributions."
    state["current_question"] = text
    state["question_count"] = state["question_count"] + 1
    return state


def build_interview_graph():
    """One step per invoke — API calls once per question."""
    graph = StateGraph(InterviewState)
    graph.add_node("generate_question", generate_question)
    graph.set_entry_point("generate_question")
    graph.add_edge("generate_question", END)
    return graph.compile()


interview_graph = build_interview_graph()
