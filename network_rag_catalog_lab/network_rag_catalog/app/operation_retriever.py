from .vectorstore import get_vectorstore
from .catalog import get_operation

def retrieve_operation_candidates(prompt,category,k=3):
    #Get the vectorstore instance (ChromaDB) using the get_vectorstore function from vectorstore.py
    vs=get_vectorstore(); 
    # Use the vs instance built-in similarity search to retrieve the top-k operation candidates from vectorstore data that contains specified category information based on the prompt and apply LLM-deduced category as the filter.
    # Beforehands, the operations.json file is vectorized and stored in ChromaDB with the operation_id as metadata and the category as a filter.
    results=vs.similarity_search_with_score(prompt,k=k,filter={'category':category})
    # From the vector return result, the operation_id is extracted in the form of d.metadata['operation_id]
    # the category using the input category, while the description using the get_operation function from catalog.py
    # that retrieves the operation description from the operations.json file(uunder data/catalog/) using the operation_id as filter.
    # The s is the score of the similarity search result, which is converted to float
    return [{'operation_id':d.metadata['operation_id'],'category':category,'description':get_operation(d.metadata['operation_id'])['description'],'score':float(s)} for d,s in results]
