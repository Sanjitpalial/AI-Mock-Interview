from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from pypdf import PdfReader
import io

from langchain.text_splitter import RecursiveCharacterTextSplitter

from sentence_transformers import SentenceTransformer

import chromadb

router = APIRouter()

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


# Ask Question API
@router.post("/ask-question")
async def ask_question(data: QuestionRequest):

    # Generate embedding for user question
    query_embedding = model.encode([data.question]).tolist()

    # Search relevant chunks
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )

    documents = results["documents"][0]

    print("RETRIEVED DOCUMENTS:", documents)

    return {
        "question": data.question,
        "retrieved_chunks": documents
    }