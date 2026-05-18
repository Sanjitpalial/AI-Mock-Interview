from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from pypdf import PdfReader
import io

from langchain_text_splitters import RecursiveCharacterTextSplitter

from sentence_transformers import SentenceTransformer

import chromadb

from groq import Groq
from dotenv import load_dotenv
import os

router = APIRouter()

# Load environment variables
load_dotenv()

# Groq client
groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# ChromaDB setup
client = chromadb.Client()

collection = client.get_or_create_collection("study_material")

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


@router.get("/")
def home():
    return {"message": "Study Assistant Running"}


# Upload PDF API
@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):

    contents = await file.read()

    pdf = PdfReader(io.BytesIO(contents))

    text = ""

    # Extract text from all pages
    for page in pdf.pages:
        extracted = page.extract_text()

        if extracted:
            text += extracted

    print("EXTRACTED TEXT:")
    print(text[:500])

    # Split text into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = splitter.split_text(text)

    print("TOTAL CHUNKS:", len(chunks))

    # If no chunks found
    if len(chunks) == 0:
        return {
            "message": "No text found in PDF"
        }

    # Delete old collection if exists
    try:
        client.delete_collection("study_material")
    except:
        pass

    # Create fresh collection
    global collection
    collection = client.get_or_create_collection("study_material")

    # Generate embeddings
    embeddings = model.encode(chunks).tolist()

    # Store in ChromaDB
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=[f"id_{i}" for i in range(len(chunks))]
    )

    print("COLLECTION COUNT:", collection.count())

    return {
        "message": "PDF processed successfully",
        "total_chunks": len(chunks)
    }


# Question model
class QuestionRequest(BaseModel):
    question: str

class QuizRequest(BaseModel):
    topic: str


# Ask Question API
@router.post("/ask-question")
async def ask_question(data: QuestionRequest):

    # Check if collection has data
    if collection.count() == 0:
        return {
            "message": "Please upload a PDF first."
        }

    # Generate embedding for question
    query_embedding = model.encode([data.question]).tolist()

    # Retrieve relevant chunks
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )

    documents = results["documents"][0]

    # If no relevant documents found
    if len(documents) == 0:
        return {
            "message": "No relevant content found."
        }

    context = "\n".join(documents)

    # Prompt for AI
    prompt = f"""
You are an AI Study Assistant.

Answer the question ONLY from the provided context.

Context:
{context}

Question:
{data.question}
"""

    print("QUESTION:", data.question)

    # Groq API call
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="llama-3.1-8b-instant"
    )

    answer = chat_completion.choices[0].message.content

    return {
        "question": data.question,
        "answer": answer,
        "retrieved_chunks": documents
    }
# Quiz Generator API
@router.post("/generate-quiz")
async def generate_quiz(data: QuizRequest):

    # Check collection
    if collection.count() == 0:
        return {
            "message": "Please upload a PDF first."
        }

    # Generate embedding
    query_embedding = model.encode([data.topic]).tolist()

    # Retrieve relevant chunks
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )

    documents = results["documents"][0]

    context = "\n".join(documents)

    # Prompt
    prompt = f"""
You are an AI Quiz Generator.

Generate 5 multiple choice questions from the provided context.

Rules:
- Each question must have 4 options
- Provide correct answer
- Keep questions simple and clear

Context:
{context}

Return format:

Q1:
Options:
A.
B.
C.
D.

Answer:
"""

    # Groq API
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="llama-3.1-8b-instant"
    )

    quiz = chat_completion.choices[0].message.content

    return {
        "topic": data.topic,
        "quiz": quiz
    }