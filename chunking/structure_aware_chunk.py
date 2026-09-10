from langchain_text_splitters import MarkdownHeaderTextSplitter

# with open("original.txt", "r") as file:
#     text = file.read()

with open("document.md", "r") as file:
    text = file.read()

headers_to_split_on = [
    # When detecting #, recognize it as "Header 1", and 
    # store the header info in metadata using the key "Header 1"
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3")
]

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

documents = splitter.split_text(text)

for document in documents:
    print(f"\n--- Document ---")
    print(document.metadata)
    print(document.page_content)