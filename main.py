# # main.py
# from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header
# from conversational_rag_chain import rag_chain_lcel, conversational_rag_chain
# from ingest import ingest_pdf
# from langchain_core.messages import HumanMessage, AIMessage
# import os
# import shutil
# from dotenv import load_dotenv


# load_dotenv()

# app = FastAPI(
#     title="RAG API Service",
#     description="LangChain + Chroma + OpenAI RAG system with PDF ingestion",
# )

# API_KEY = os.getenv('OPENAI_API_KEY')

# UPLOAD_DIR = "./uploaded_pdfs"
# os.makedirs(UPLOAD_DIR, exist_ok=True)
# chat_histories = {}

# def verify_api_key(x_api_key: str = Header(...)):
#     if x_api_key != API_KEY:
#         raise HTTPException(status_code=401, detail="Invalid API key")

# @app.get("/")
# def root():
#     return {"message": "Welcome to the RAG API service!"}

# @app.post("/upload-pdf", dependencies=[Depends(verify_api_key)])
# async def upload_pdf(file: UploadFile = File(...)):
#     """
#     Upload a PDF and index it into ChromaDB.
#     """
#     try:
#         file_path = os.path.join(UPLOAD_DIR, file.filename)
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         result = ingest_pdf(file_path)
#         return {"status": "success", **result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/query/basic", dependencies=[Depends(verify_api_key)])
# def query_basic(question: str):
#     """
#     Query the RAG system (no conversation memory).
#     """
#     try:
#         answer = rag_chain_lcel.invoke(question)
#         return {"question": question, "answer": answer}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/query/conversational", dependencies=[Depends(verify_api_key)])
# def query_conversational(session_id: str, question: str):
#     """
#     Query the conversational RAG chain with chat memory.
#     """
#     try:
#         chat_history = chat_histories.get(session_id, [])
#         result = conversational_rag_chain.invoke({
#             "chat_history": chat_history,
#             "input": question
#         })

#         chat_history.extend([
#             HumanMessage(content=question),
#             AIMessage(content=result["answer"])
#         ])
#         chat_histories[session_id] = chat_history

#         return {
#             "session_id": session_id,
#             "question": question,
#             "answer": result["answer"]
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
