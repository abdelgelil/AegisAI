from typing import List, Dict, Any
import uuid

class DocumentChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str, page_number: int = 1, section: str = "General") -> List[Dict[str, Any]]:
        """
        Splits raw text into overlapping chunks and associates metadata 
        (page number, section, position) matching your ERD contract.
        """
        words = text.split()
        chunks = []
        
        if not words:
            return chunks

        position = 0
        i = 0
        while i < len(words):
            end_idx = min(i + self.chunk_size, len(words))
            chunk_words = words[i:end_idx]
            chunk_text = " ".join(chunk_words)

            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "text": chunk_text,
                "position": position,
                "page_number": page_number,
                "section": section
            })

            position += 1
            # Move forward by chunk_size minus overlap
            i += (self.chunk_size - self.chunk_overlap)

        return chunks