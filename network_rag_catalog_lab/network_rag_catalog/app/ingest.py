from langchain_core.documents import Document
from langchain_chroma import Chroma
from .catalog import load_operations
from .config import CHROMA_DIR,CHROMA_COLLECTION
from .embeddings import embeddings

def build_document(op):
    text=f"Operation ID: {op['operation_id']}\nCategory: {op['category']}\nName: {op['name']}\nDescription: {op['description']}\nUse cases:\n"+'\n'.join('- '+x for x in op.get('use_cases',[]))
    return Document(page_content=text,metadata={'operation_id':op['operation_id'],'category':op['category']})

def ingest():
    ops=load_operations(); docs=[build_document(x) for x in ops]; ids=[x['operation_id'] for x in ops]
    CHROMA_DIR.mkdir(parents=True,exist_ok=True)
    vs=Chroma(collection_name=CHROMA_COLLECTION,persist_directory=str(CHROMA_DIR),embedding_function=embeddings)
    old=vs.get()
    if old.get('ids'): vs.delete(ids=old['ids'])
    vs.add_documents(docs,ids=ids)
    print(f'Indexed {len(docs)} operations into {CHROMA_DIR}')
if __name__=='__main__': ingest()
