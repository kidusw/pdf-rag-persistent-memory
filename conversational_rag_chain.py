# # rag_chain.py
# from langchain_community.vectorstores import Chroma
# from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# from langchain.chains.retrieval import create_retrieval_chain
# from langchain.chains.history_aware_retriever import create_history_aware_retriever
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnablePassthrough
# from langchain_classic.chains.combine_documents import create_stuff_documents_chain
# from langchain_core.messages import HumanMessage, AIMessage
# from langchain_classic.chat_models import init_chat_model
# from dotenv import load_dotenv

# import os

# load_dotenv()

# groq_api_key = os.getenv("GROQ_API_KEY")

# API_KEY = os.getenv('OPENAI_API_KEY')

# # persist_directory = "./chroma_db"
# # collection_name = "rag_collection"

# PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
# COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "rag_collection")

# # Initialize embeddings and vectorstore
# embedding = OpenAIEmbeddings()
# vectorstore = Chroma(
#     persist_directory=PERSIST_DIR,
#     embedding_function=embedding,
#     collection_name=COLLECTION_NAME,
# )

# # Use GPT model
# # llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3,api_key=API_KEY)
# llm=init_chat_model(model="groq:groq/compound-mini",temperature=0.4)
# # === Basic Retriever ===
# retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# # === LCEL Chain ===
# custom_prompt = ChatPromptTemplate.from_template("""
# Use the following context to answer the question. 
# If you don't know the answer, say "I don't know."
# Provide specific details from the context.

# Context:
# {context}

# Question: {question}

# Answer:
# """)

# def format_docs(docs):
#     return "\n\n".join(doc.page_content for doc in docs)

# rag_chain_lcel = (
#     {
#         "context": retriever | format_docs,
#         "question": RunnablePassthrough()
#     }
#     | custom_prompt
#     | llm
#     | StrOutputParser()
# )

# # === Conversational Chain ===
# contextualize_q_system_prompt = """Given a chat history and the latest user question 
# which might reference context in the chat history, formulate a standalone question 
# which can be understood without the chat history. Do NOT answer the question."""
# contextualize_q_prompt = ChatPromptTemplate.from_messages([
#     ("system", contextualize_q_system_prompt),
#     MessagesPlaceholder("chat_history"),
#     ("human", "{input}"),
# ])

# history_aware_retriever = create_history_aware_retriever(
#     llm, retriever, contextualize_q_prompt
# )

# qa_prompt = ChatPromptTemplate.from_messages([
#     ("system", """You are an assistant for question-answering tasks. 
# Use retrieved context to answer. If unknown, say you don't know.


# Context: {context}"""),
#     MessagesPlaceholder("chat_history"),
#     ("human", "{input}"),
# ])

# question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

# conversational_rag_chain = create_retrieval_chain(
#     history_aware_retriever, question_answer_chain
# )
