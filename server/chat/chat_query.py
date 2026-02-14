import os
import asyncio
import requests
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --------------------------------------------------
# Load Environment Variables
# --------------------------------------------------
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
SCALEDOWN_API_KEY = os.getenv("SCALEDOWN_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# --------------------------------------------------
# Initialize Pinecone
# --------------------------------------------------
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# --------------------------------------------------
# Initialize Embedding Model
# --------------------------------------------------
embed_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001"
)

# --------------------------------------------------
# ScaleDown Config
# --------------------------------------------------
SCALEDOWN_URL = "https://api.scaledown.xyz/compress/raw/"

headers = {
    "x-api-key": SCALEDOWN_API_KEY,
    "Content-Type": "application/json"
}


# ==================================================
# Main Query Function
# ==================================================
async def answer_query(query: str):

    try:
        # ------------------------------------------
        # Step 1: Embed User Query
        # ------------------------------------------
        embedding = await asyncio.to_thread(
            embed_model.embed_query, query
        )

        # ------------------------------------------
        # Step 2: Retrieve Relevant Docs from Pinecone
        # ------------------------------------------
        results = await asyncio.to_thread(
            index.query,
            vector=embedding,
            top_k=3,
            include_metadata=True
        )

        contexts = []
        sources = set()

        for match in results.matches:
            metadata = match.metadata or {}
            contexts.append(metadata.get("text", ""))
            sources.add(metadata.get("source"))

        if not contexts:
            return {
                "answer": "No relevant information found.",
                "sources": []
            }

        docs_text = "\n".join(contexts)

        # ------------------------------------------
        # Step 3: Send to ScaleDown API
        # ------------------------------------------
        payload = {
            "context": docs_text,
            "prompt": query,
            "model": "gpt-4o",
            "scaledown": {
                "rate": "auto"
            }
        }

        response = await asyncio.to_thread(
            requests.post,
            SCALEDOWN_URL,
            headers=headers,
            json=payload,   # ✅ safer than data=json.dumps
            timeout=60
        )

        # ------------------------------------------
        # Step 4: Handle HTTP Errors
        # ------------------------------------------
        if response.status_code != 200:
            return {
                "answer": f"ScaleDown API error: {response.status_code}",
                "sources": list(sources)
            }

        result = response.json()

        # ------------------------------------------
        # Step 5: Extract Answer Safely
        # ------------------------------------------
        answer_text = (
            result.get("results", {})
                  .get("compressed_prompt", None)
        )

        if not answer_text:
            answer_text = "Failed to generate response."

        # ------------------------------------------
        # Final Return
        # ------------------------------------------
        return {
            "answer": answer_text,
            "sources": list(sources)
        }

    except Exception as e:
        return {
            "answer": f"Internal error: {str(e)}",
            "sources": []
        }
