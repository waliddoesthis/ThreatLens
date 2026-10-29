"""Split documents into overlapping word windows.

Simple on purpose: the chunk-size ablation in M2 compares settings of this function.
Short docs (most ATT&CK / KEV records) stay as a single chunk.
"""

from threatlens.schema import Chunk, Document


def chunk_document(doc: Document, size: int = 220, overlap: int = 40) -> list[Chunk]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    words = doc.text.split()
    if not words:
        return []
    chunks, start, n = [], 0, 0
    while True:
        window = words[start : start + size]
        body = " ".join(window)
        # repeat the title in every chunk after the first so each chunk is self-describing
        text = body if n == 0 else f"{doc.title}\n{body}"
        chunks.append(
            Chunk(
                chunk_id=f"{doc.id}#{n}",
                doc_id=doc.id,
                source=doc.source,
                title=doc.title,
                text=text,
                url=doc.url,
                metadata=doc.metadata,
            )
        )
        if start + size >= len(words):
            break
        start += size - overlap
        n += 1
    return chunks
