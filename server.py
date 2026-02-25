# main.py
import os
import shutil
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Form, HTTPException, UploadFile, File, Header, Query
from typing import List, Optional
import uuid

from ragchain import get_vectorstore,RagChain
from ingestion import ingest_pdf, ingest_pdfs, reindex_all
from db import save_chat_history, load_chat_history, clear_chat_history
from langchain_core.messages import HumanMessage, AIMessage
from mongo_db import ChatHistory
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Config    
API_KEY = os.getenv("API_KEY", "mysecretapikey")  # simple key; keep secure
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploaded_pdfs")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")



chat = ChatHistory()
rag_chain = RagChain(api_key=OPENAI_API_KEY)

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="RAG API Service (with batch ingest & persistence)")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/")
def root():
    return {"message": "RAG API service is running."}

# -----------------------
# Batch PDF upload
# -----------------------
# dependencies=[Depends(verify_api_key)]
@app.post("/upload-pdfs")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    """
    Upload multiple PDFs at once and ingest them into Chroma.
    """
    saved_paths = []
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            continue
        dest = os.path.join(UPLOAD_DIR, f.filename)
        with open(dest, "wb") as buf:
            shutil.copyfileobj(f.file, buf)
        saved_paths.append(dest)

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No PDF files uploaded.")

    results = ingest_pdfs(saved_paths)
    # warm the vectorstore after ingestion
    try:
        rag_chain.get_vectorstore()
        # get_vectorstore()
    except Exception:
        pass

    return {"status": "success", "ingested": results}

# -----------------------
# Reindex endpoint
# -----------------------
@app.post("/reindex", dependencies=[Depends(verify_api_key)])
def reindex():
    """
    Rebuild the Chroma collection from all PDFs present in UPLOAD_DIR.
    WARNING: This clears previous Chroma data.
    """
    result = reindex_all(UPLOAD_DIR)
    try:
        rag_chain.get_vectorstore()
        get_vectorstore()
    except Exception as e:
        pass
    return {"status": "success", "reindexed": result}

# -----------------------
# Query endpoints
# -----------------------
# @app.post("/query/basic", dependencies=[Depends(verify_api_key)])
# def query_basic(question: str = Query(..., description="Question to ask the RAG system")):
#     try:
#         answer = rag_chain_lcel.invoke(question)
#         return {"question": question, "answer": answer}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.post("query/new_chat")
def create_chat(session_id:Optional[str]):
    new_chat = chat.new_chat(session_id)
    return new_chat

@app.post("/query/conversational")
def query_conversational(session_id: Optional[str] = Query(...), question: str = Form(...)):
    """
    If session_id omitted, a new session_id will be created and returned.
    Chat history is persisted in SQLite or Redis (if REDIS_URL set).

    """
    print("session_id",session_id)
    try:
        if not session_id:
            session_id = str(uuid.uuid4())
        # messages = load_chat_history(session_id)  # list of dicts {"role","content"}
        messages = chat.load_chat_history(session_id)

            
        print(f"messages: {messages}")
        # Convert to langchain messages
        chat_history = []
        for m in messages:
            if m["role"] == "human":
                chat_history.append(HumanMessage(content=m["content"]))
            else:
                chat_history.append(AIMessage(content=m["content"]))
       

        result = rag_chain.rag_chain_with_lcel().invoke({
            "chat_history": chat_history,
            "input": question
        })

        print("result:",result)

        pdf_file_path = result['context'][0].metadata['source'].split("\\")[1]
        print(f'file_path:{pdf_file_path}')
        # Append and persist
        print(f"results{result['context'][0].metadata['source']}")
        messages.append({"role": "human", "content": question})
        messages.append({"role": "ai", "content": result["answer"]})
        chat.save_chat_history(session_id, messages,question)

        return {"session_id": session_id, "question": question, "answer": result["answer"],'source':pdf_file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------
# Chat management endpoints
# -----------------------

@app.get("/chat/all")
def get_all():
    all_chat = chat.load_all()
    contents = all_chat
        
    return JSONResponse(content=contents)


@app.get("/chat/{session_id}")
def get_chat(session_id: str):
    print("session_id",session_id)
    messages = chat.load_chat_history(session_id)
    content = {"session_id": session_id, "messages": messages}
    return JSONResponse(content=content )


@app.delete("/chat/{session_id}", dependencies=[Depends(verify_api_key)])
def delete_chat(session_id: str):
    clear_chat_history(session_id)
    return {"status": "deleted", "session_id": session_id}
