from app.database import db
from app.database import (
    pdf_collection,
    chat_collection,
    notes_collection,
    quiz_collection,
    flashcard_collection,
    roadmap_collection
)  
from langchain.memory import ConversationBufferMemory
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

# Conversation Memory
memory = ConversationBufferMemory(
    return_messages=True
)

# ChromaDB setup
client = chromadb.Client()

# Create collection only once
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

    # Generate embeddings
    embeddings = model.encode(chunks).tolist()

    # Store in ChromaDB
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=[
            {"source": file.filename}
            for _ in range(len(chunks))
        ],
        ids=[
            f"{file.filename}_{i}"
            for i in range(len(chunks))
        ]
    )

    print("COLLECTION COUNT:", collection.count())
    pdf_collection.insert_one({
    "file_name": file.filename,
    "total_chunks": len(chunks)
    })

    return {
        "message": "PDF processed successfully",
        "file_name": file.filename,
        "total_chunks": len(chunks)
    }


# Request Models
class QuestionRequest(BaseModel):
    question: str
    pdf_name: str = None


class QuizRequest(BaseModel):
    topic: str


class FlashcardRequest(BaseModel):
    topic: str

class RoadmapRequest(BaseModel):
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
    if data.pdf_name:
        results = collection.query(
        query_embeddings=query_embedding,
        n_results=3,
        where={"source": data.pdf_name}
        )
    else:
        results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
        )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    # If no relevant documents found
    if len(documents) == 0:
        return {
            "message": "No relevant content found."
        }

    context = "\n".join(documents)

    # Conversation history
    chat_history = memory.load_memory_variables({})

    history = chat_history.get("history", "")

    # Prompt
    prompt = f"""
You are an AI Study Assistant.

Use the conversation history and provided context
to answer the user's question.

IMPORTANT RULES:
- Answer ONLY from the provided context
- If answer is not in context, say:
  "This information is not available in the uploaded PDF."
- Keep answers simple and student friendly
- Do not make up information

Conversation History:
{history}

Context:
{context}

Question:
{data.question}

Answer:
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

    # Save memory
    memory.save_context(
        {"input": data.question},
        {"output": answer}
    )

    # Extract sources
    sources = list(set([
        metadata["source"]
        for metadata in metadatas
    ]))
    chat_collection.insert_one({
    "question": data.question,
    "answer": answer,
    "sources": sources
    })

    return {
        "question": data.question,
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": documents
    }


# Generate Notes API
@router.post("/generate-notes")
async def generate_notes():

    # Check collection
    if collection.count() == 0:
        return {
            "message": "Please upload a PDF first."
        }

    # Get all stored documents
    results = collection.get()

    documents = results["documents"]

    # Combine all text
    full_text = "\n".join(documents)

    # Prompt
    prompt = f"""
You are an AI Notes Generator.

Create well-structured study notes from the following content.

Rules:
- concise
- easy to revise
- point-wise
- student friendly
- include headings

Content:
{full_text}
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

    notes = chat_completion.choices[0].message.content
    notes_collection.insert_one({
    "notes": notes
    })

    return {
        "generated_notes": notes
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
- Questions should come ONLY from context

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
    quiz_collection.insert_one({
    "topic": data.topic,
    "quiz": quiz
    })

    return {
        "topic": data.topic,
        "quiz": quiz
    }


# Flashcard Generator API
@router.post("/generate-flashcards")
async def generate_flashcards(data: FlashcardRequest):

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
        n_results=5
    )

    documents = results["documents"][0]

    context = "\n".join(documents)

    # Prompt
    prompt = f"""
Create 5 flashcards from the provided context.

Rules:
- Keep answers short
- Student friendly
- Only use provided context

Format:

Q:
A:

Context:
{context}
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

    flashcards = chat_completion.choices[0].message.content
    flashcard_collection.insert_one({
    "topic": data.topic,
    "flashcards": flashcards
    })

    return {
        "topic": data.topic,
        "flashcards": flashcards
    }


@router.get("/uploaded-pdfs")
async def uploaded_pdfs():

    results = collection.get()

    metadatas = results["metadatas"]

    pdfs = list(set([
        metadata["source"]
        for metadata in metadatas
    ]))

    return {
        "uploaded_pdfs": pdfs,
        "total_pdfs": len(pdfs)
    }   

@router.delete("/delete-pdf/{pdf_name}")
async def delete_pdf(pdf_name: str):

    # Get all documents
    results = collection.get()

    ids_to_delete = []
    metadatas = results["metadatas"]
    ids = results["ids"]

    # Find matching PDF chunks
    for i, metadata in enumerate(metadatas):

        if metadata["source"] == pdf_name:
            ids_to_delete.append(ids[i])

    # If no PDF found
    if len(ids_to_delete) == 0:
        return {
            "message": f"{pdf_name} not found."
        }

    # Delete chunks
    collection.delete(ids=ids_to_delete)

    return {
        "message": f"{pdf_name} deleted successfully.",
        "deleted_chunks": len(ids_to_delete)
    }

# Study Roadmap Generator API
@router.post("/generate-roadmap")
async def generate_roadmap(data: RoadmapRequest):

    prompt = f"""
You are an AI Study Roadmap Generator.

Create a complete learning roadmap for:
{data.topic}

Rules:
- Beginner to advanced progression
- Step-by-step structure
- Include phases or weeks
- Mention important concepts
- Student friendly
- Easy to follow

Format example:

Phase 1:
- Topic 1
- Topic 2

Phase 2:
- Topic 3
- Topic 4
"""

    try:

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.1-8b-instant"
        )

        roadmap = chat_completion.choices[0].message.content
        roadmap_collection.insert_one({
    "topic": data.topic,
    "roadmap": roadmap
    })

        return {
            "topic": data.topic,
            "roadmap": roadmap
        }

    except Exception as e:

        return {
            "message": "Roadmap generation failed.",
            "error": str(e)
        }