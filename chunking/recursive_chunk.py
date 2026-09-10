from langchain_text_splitters import RecursiveCharacterTextSplitter

with open("original.txt", "r") as file:
    text = file.read()

# FUNCTION DEFINTION
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=[
        "\n\n",
        "\n",
        " ",
        "",
    ]
)

# FUNCTION CALLING
chunks = splitter.split_text(text)

for i, chunk in enumerate(chunks):
    print(f"\n--- Chunk {i + 1} ---")
    print(chunk)