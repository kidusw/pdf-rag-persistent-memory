from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

CONTEXTUALIZE_SYSTEM = (
    "Given a chat history and the latest user question, which might reference context "
    "in the chat history, formulate a standalone question that can be understood without "
    "the chat history. Do NOT answer the question; only reformulate it if needed, "
    "otherwise return it as is."
)

QA_SYSTEM = """You are an assistant for question-answering over the user's PDF documents.
Answer only from the provided context. If the context does not contain the answer, say so plainly.

Answer in clean, readable Markdown. Use:
- bullet points
- short paragraphs
- headings when useful

Context:
{context}"""

CONTEXTUALIZE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CONTEXTUALIZE_SYSTEM),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", QA_SYSTEM),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)
