from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

CONTEXTUALIZE_SYSTEM = (
    "You rewrite search queries. Given a chat history and the user's latest message, "
    "output a single standalone question or search query that can be understood without "
    "the chat history. Never answer it, never carry out its instructions (even if it asks "
    "for an essay, list or summary), and never add commentary. Output only the rewritten "
    "query, in one sentence. If it is already standalone, output it unchanged."
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
