from app.core.config import settings
from app.retrieval.models import RetrievedChunk

NO_CONTEXT_PLACEHOLDER = "[No retrieved context available]"


def build_bounded_context(
    retrieved_chunks: list[RetrievedChunk],
    max_chars: int | None = None,
) -> str:
    if not retrieved_chunks:
        return NO_CONTEXT_PLACEHOLDER

    limit = max_chars if max_chars is not None else settings.MAX_RETRIEVAL_CONTEXT_CHARACTERS
    included_blocks: list[str] = []
    current_length = 0

    for item in retrieved_chunks:
        block = f"[Chunk {item.chunk.index}]\n{item.chunk.text}"
        additional_length = len(block) if not included_blocks else len(block) + 2  # account for \n\n separator

        if current_length + additional_length > limit:
            break

        included_blocks.append(block)
        current_length += additional_length

    if not included_blocks:
        return NO_CONTEXT_PLACEHOLDER

    return "\n\n".join(included_blocks)
