import json
from typing import Any

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk


def parse_sse(text: str) -> list[tuple[str, Any]]:
    events = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        if not block.strip():
            continue
        fields = dict(line.split(": ", 1) for line in block.split("\n") if ": " in line)
        events.append((fields["event"], json.loads(fields["data"])))
    return events


class FailingAfterFirstTokenLLM(GenericFakeChatModel):
    """Streams one chunk, then fails the way a rate-limited provider would."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(messages=iter([]), **kwargs)

    def _stream(self, messages, *args: Any, **kwargs: Any):
        yield ChatGenerationChunk(message=AIMessageChunk(content="Partial"))
        raise RuntimeError("rate limited")
