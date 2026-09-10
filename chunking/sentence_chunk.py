import re

# FILE READING
with open("original.txt", "r", encoding="utf-8") as file:
    text = file.read()

# FUNCTION DEFINITIONS
def split_sentences(text):
    # Regular expression pattern to match sentence endings
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    # Split the text into sentences using the regex pattern
    sentences = sentence_endings.split(text) 
    # Remove any leading/trailing whitespace from each sentence
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    
    return sentences

def sentence_chunk(text, max_chars=500):
    sentences = split_sentences(text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if (len(current_chunk) + len(sentence) + 1 <= max_chars):  # +1 for space or punctuation
            current_chunk += " " + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip()) # Add accumulated chunk to the list
                current_chunk = sentence  # Start new chunk with the current sentence that cannot be added to the previous chunk

    if current_chunk:
        chunks.append(current_chunk.strip())  # Add the last chunk if it exists

    return chunks

# FUNCTION CALLING
chunks = sentence_chunk(text, max_chars=500)

# PRINTING RESULTS
for i, chunk in enumerate(chunks):
    print(f"\n--- Chunk {i + 1} ---")
    print(chunk)