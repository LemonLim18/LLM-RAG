from .vectorstore import get_vectorstore
from .catalog import get_operation

def retrieve_operation_candidates(prompt,category,k=3):
    vs=get_vectorstore(); results=vs.similarity_search_with_score(prompt,k=k,filter={'category':category})
    return [{'operation_id':d.metadata['operation_id'],'category':category,'description':get_operation(d.metadata['operation_id'])['description'],'score':float(s)} for d,s in results]
