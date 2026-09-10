# FILE READING
with open("original.txt", "r", encoding="utf-8") as file:
    text = file.read()

# FUNCTION DECLARATIONS
def fixed_size_chunk(text, chunk_size=500):
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)

    return chunks

def fixed_size_chunk_with_overlap(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

# FUNCTION CALLING
chunks = fixed_size_chunk(text, chunk_size=500)
chunks_with_overlap = fixed_size_chunk_with_overlap(text, chunk_size=500, overlap=100)

# PRINTING RESULTS
# for i, chunk in enumerate(chunks):
#     print(f"\n--- Chunk {i + 1} ---")
#     print(chunk)

for i, chunk in enumerate(chunks_with_overlap):
    print(f"\n--- Chunk {i + 1} ---")
    print(chunk)

    if i > 0:
        print("\n>>> OVERLAPPING PART <<<")
        print(chunk[:100])
    print("\n>>> END OF OVERLAPPING PART <<<")

