# FILE READING
with open("original.txt", "r", encoding="utf-8") as file:
    text = file.read()

# FUNCTION DECLARATIONS
def paragraph_chunk(text, max_chars=500):
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if(len(current_chunk) + len(paragraph) <= max_chars):
            if current_chunk:
                current_chunk += "\n\n"
            current_chunk += paragraph
        else:
            # Save previous chunk
            if current_chunk:
                chunks.append(current_chunk)
            # Start new chunk with current paragraph
            current_chunk = paragraph
    # Save final chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks

# FUNCTION CALLING
chunks = paragraph_chunk(text, max_chars=500)

# PRINTING RESULTS
for i, chunk in enumerate(chunks):
    print(f"\n--- Chunk {i + 1} ---")
    print(chunk)
