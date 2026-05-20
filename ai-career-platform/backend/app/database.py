from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)

db = client["ai_study_assistant"]

# Collections
pdf_collection = db["pdfs"]

chat_collection = db["chat_history"]

notes_collection = db["notes"]

quiz_collection = db["quizzes"]

flashcard_collection = db["flashcards"]

roadmap_collection = db["roadmaps"]

print("MongoDB Connected Successfully")