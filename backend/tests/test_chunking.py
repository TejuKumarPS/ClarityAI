import pytest
from app.chunking.models import DocumentChunk, ChunkingMetadata
from app.chunking.chunker import CharacterChunker
from app.chunking.exceptions import (
    ChunkingError,
    InvalidChunkConfigurationError,
    EmptyDocumentError,
)


# ==========================================
# 1. Configuration Validation Tests
# ==========================================

def test_chunker_valid_default_configuration():
    chunker = CharacterChunker()
    assert chunker.chunk_size == 4000
    assert chunker.chunk_overlap == 400


def test_chunker_custom_valid_configuration():
    chunker = CharacterChunker(chunk_size=100, chunk_overlap=20)
    assert chunker.chunk_size == 100
    assert chunker.chunk_overlap == 20


@pytest.mark.parametrize(
    "size,overlap",
    [
        (0, 0),        # size must be > 0
        (-10, 0),      # size negative
        (100, -5),     # overlap negative
        (100, 100),    # overlap cannot equal size
        (100, 150),    # overlap cannot exceed size
    ],
)
def test_chunker_invalid_configuration_raises(size, overlap):
    with pytest.raises(InvalidChunkConfigurationError):
        CharacterChunker(chunk_size=size, chunk_overlap=overlap)


# ==========================================
# 2. Input Validation Tests
# ==========================================

def test_chunker_empty_input_raises():
    chunker = CharacterChunker(chunk_size=50, chunk_overlap=10)
    with pytest.raises(EmptyDocumentError):
        chunker.chunk("")


def test_chunker_whitespace_only_raises():
    chunker = CharacterChunker(chunk_size=50, chunk_overlap=10)
    with pytest.raises(EmptyDocumentError):
        chunker.chunk("   \n\t  \n   ")


# ==========================================
# 3. Basic Chunking Tests
# ==========================================

def test_chunker_short_text_single_chunk():
    chunker = CharacterChunker(chunk_size=100, chunk_overlap=20)
    text = "Short transcript under 100 chars."
    chunks = chunker.chunk(text)

    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].text == text
    assert chunks[0].start_char == 0
    assert chunks[0].end_char == len(text)


def test_chunker_exact_chunk_size_single_chunk():
    chunker = CharacterChunker(chunk_size=20, chunk_overlap=5)
    text = "12345678901234567890"  # length 20
    chunks = chunker.chunk(text)

    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].text == text
    assert chunks[0].start_char == 0
    assert chunks[0].end_char == 20


# ==========================================
# 4. Interval Coverage & Invariant Tests
# ==========================================

@pytest.mark.parametrize(
    "text_len,chunk_size,overlap",
    [
        (50, 10, 2),
        (55, 10, 3),
        (100, 30, 10),
        (350, 80, 20),
        (1000, 250, 50),
        (73, 25, 7),
    ],
)
def test_chunker_interval_coverage_and_continuity(text_len, chunk_size, overlap):
    # Generate synthetic deterministic text
    text = "".join([chr(65 + (i % 26)) for i in range(text_len)])
    chunker = CharacterChunker(chunk_size=chunk_size, chunk_overlap=overlap)
    chunks = chunker.chunk(text)

    assert len(chunks) > 1

    # 1. Begins at 0
    assert chunks[0].start_char == 0

    # 2. Final chunk reaches the exact end of the source text
    assert chunks[-1].end_char == text_len

    stride = chunk_size - overlap

    for i, chunk in enumerate(chunks):
        # 3. 0-based sequential ordering
        assert chunk.index == i

        # 4. Strict substring boundary invariant: text[start:end] == chunk.text
        assert text[chunk.start_char:chunk.end_char] == chunk.text
        assert len(chunk.text) == (chunk.end_char - chunk.start_char)

        # 5. Stride and continuity check against adjacent chunk
        if i < len(chunks) - 1:
            next_chunk = chunks[i + 1]
            assert next_chunk.start_char == chunk.start_char + stride
            # No gaps: next chunk starts before current chunk ends
            assert next_chunk.start_char < chunk.end_char
            # Overlap equality
            expected_overlap_text = chunk.text[stride:chunk_size]
            assert next_chunk.text.startswith(expected_overlap_text)


def test_chunker_final_chunk_remainder_smaller_than_chunk_size():
    chunker = CharacterChunker(chunk_size=10, chunk_overlap=2)
    # Length 23 -> stride = 8 -> Chunks: [0, 10), [8, 18), [16, 23)
    text = "ABCDEFGHIJKLMNOPQRSTUVW"
    assert len(text) == 23

    chunks = chunker.chunk(text)
    assert len(chunks) == 3

    assert chunks[0].start_char == 0
    assert chunks[0].end_char == 10
    assert chunks[0].text == "ABCDEFGHIJ"

    assert chunks[1].start_char == 8
    assert chunks[1].end_char == 18
    assert chunks[1].text == "IJKLMNOPQR"

    assert chunks[2].start_char == 16
    assert chunks[2].end_char == 23
    assert chunks[2].text == "QRSTUVW"

    # Final chunk reached end of text
    assert chunks[-1].end_char == len(text)


def test_chunker_determinism():
    chunker = CharacterChunker(chunk_size=30, chunk_overlap=10)
    text = "The quarterly executive leadership meeting reviewed the cloud roadmap and confirmed rollout."
    run1 = chunker.chunk(text)
    run2 = chunker.chunk(text)

    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2):
        assert c1.index == c2.index
        assert c1.start_char == c2.start_char
        assert c1.end_char == c2.end_char
        assert c1.text == c2.text
