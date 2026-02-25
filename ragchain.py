# rag_chain.py
import os
from dotenv import load_dotenv
load_dotenv()

from typing import Callable
# from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_chroma import Chroma
from langchain_core.runnables import RunnableMap
# Config
PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_persist")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "rag_collection")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_vectorstore = None

class RagChain:

    def __init__(self,api_key):
        self.embedder = OpenAIEmbeddings(api_key=api_key)
        self.llm = ChatOpenAI(api_key=api_key, model=MODEL_NAME, temperature=0.7)
        self.vector_Store = Chroma(persist_directory=PERSIST_DIR,
            embedding_function=self.embedder,
            collection_name=COLLECTION_NAME,)
        self.retriver = self.vector_Store.as_retriever()
    
    def rag_chain_with_lcel(self):
         llm = self.llm
         retriever = self.retriver

         contextualize_q_system_prompt = """Given a chat history and the latest user question 
which might reference context in the chat history, formulate a standalone question 
which can be understood without the chat history. Do NOT answer the question."""
         contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
         history_aware_retriever = create_history_aware_retriever(
             llm, retriever, contextualize_q_prompt
         )
        
         qa_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an assistant for question-answering tasks. 
Use retrieved context to answer.
         Answer: Provide a comprehensive answer based on the research findings above
        Answer the user's question in clean, readable Markdown.
        Use:
- bullet points
- short paragraphs
- headings when useful
.

Context: {context}"""),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
         question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

         conversational_rag_chain = create_retrieval_chain(
        history_aware_retriever, question_answer_chain
    )
        

         return conversational_rag_chain

    def get_vectorstore(self):
        global _vectorstore
        if _vectorstore is None:
            embeddings = self.embedder
            # Construct Chroma object pointing at persisted directory/collection
            _vectorstore = Chroma(
                persist_directory=PERSIST_DIR,
                embedding_function=embeddings,
                collection_name=COLLECTION_NAME,
            )
        return _vectorstore

# Create embedding & llm factories that respect env var
def get_embedding():    
    return OpenAIEmbeddings(api_key=OPENAI_API_KEY)

def get_llm():
    return ChatOpenAI(api_key=OPENAI_API_KEY, model=MODEL_NAME, temperature=0.2)

# Lazily initialize vectorstore so ingest can write first
_vectorstore = None
def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        embeddings = get_embedding()
        # Construct Chroma object pointing at persisted directory/collection
        _vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
        )
    return _vectorstore

# Retriever helper
def get_retriever(k: int = 3):
    vs = get_vectorstore()
    return vs.as_retriever(search_kwargs={"k": k})

# Build LCEL chain (simple QA)
def build_lcel_chain():
    llm = get_llm()
    retriever = get_retriever()
    custom_prompt = ChatPromptTemplate.from_template(
        """Use the following context to answer the question. 
If you don't know the answer, say "I don't know." Keep answers concise.

Context:
{context}

Question: {question}

Answer:"""
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain_lcel = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | custom_prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain_lcel



# Build conversational chain (history aware)
# def build_conversational_chain():


#     llm = get_llm()
#     retriever = get_retriever()

#     contextualize_q_system_prompt = """Given a chat history and the latest user question 
# which might reference context in the chat history, formulate a standalone question 
# which can be understood without the chat history. Do NOT answer the question."""
#     contextualize_q_prompt = ChatPromptTemplate.from_messages([
#         ("system", contextualize_q_system_prompt),
#         MessagesPlaceholder("chat_history"),
#         ("human", "{input}"),
#     ])

#     history_aware_retriever = create_history_aware_retriever(
#         llm, retriever, contextualize_q_prompt
#     )


#     qa_prompt = ChatPromptTemplate.from_messages([
#         ("system", """You are an assistant for question-answering tasks. 
# Use retrieved context to answer. If unknown, say you don't know.
# Keep answers concise (max 3 sentences).

# Context: {context}"""),
#         MessagesPlaceholder("chat_history"),
#         ("human", "{input}"),
#     ])

#     question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

#     conversational_rag_chain = create_retrieval_chain(
#         history_aware_retriever, question_answer_chain
#     )

#     return conversational_rag_chain

# # Expose ready-made chains (constructed on import)
# rag_chain_lcel = build_lcel_chain()
# conversational_rag_chain = build_conversational_chain()
