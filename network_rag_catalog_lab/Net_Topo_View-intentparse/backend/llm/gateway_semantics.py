"""Semantic workflow examples, not an engineering operation catalog.

No user content is cached. Similarity selects capabilities only; V9 retains all
operation recognition and schema/rendering authority. Ambiguous matches defer
to the structured chat router instead of silently guessing an action.
"""
import math
import os

EXAMPLES={
 'answer':['Hello how are you?','What is the difference between OSPF and BGP?','What is one plus one?','Explain how routing protocols work in general','How do I configure OSPF? Explain the commands','Thanks for the help'],
 'analyze_files':['Read this uploaded PDF and summarize its contents','What does this screenshot show?','Can you read the content inside the document?','Describe the diagram on page 4','Summarize the attached log file'],
 'explain':['Explain this section of code in my editor','What does the active Jinja template do?','Why does the selected Ansible task use state merged?'],
 'edit':['Change the OSPF router ID in the open configuration','Refactor this Python code','Modify that parameter in the previous configuration','Fix the indentation in this YAML file','Adjust the BGP timers in the open code buffer'],
 'generate_native':['Generate native OSPF and BGP configuration on R1','Configure a static route on R2','Create vendor CLI configuration for Cisco and Juniper devices'],
 'generate_playbook':['Create an Ansible YAML playbook to set up OSPF','Generate an Ansible automation playbook for multiple vendors'],
 'network_inventory':['List the routers recorded in our inventory','How many Cisco devices are stored?','Which devices are in our Penang site?'],
 'network_topology':['Show current network topology','What is connected to R1?','Find the planned path between R1 and R2'],
 'network_telemetry':['Show CPU and memory measurements','What is R1 bandwidth utilization?','Show live packet loss statistics'],
 'network_syslog':['Read recent device syslog events','Show the network logs for R1'],
 'network_incidents':['Show incident and anomaly history','What alerts were recorded yesterday?'],
 'network_configuration':['Show configuration history for that router','Read the stored running configuration for R1'],
 'network_investigation':['Investigate R1 packet loss using logs and metrics','Diagnose the cause of this network outage using available evidence','Correlate topology, telemetry and configuration changes'],
}


async def semantic_hint(prompt):
    if os.getenv('COGNISHIELD_SEMANTIC_EMBEDDINGS','1')!='1' or len(prompt)>4000: return None
    from lab_config import LOCAL_OLLAMA_URL
    from llm.ollama_provider import OllamaProvider
    import httpx
    items=[(intent,text) for intent,examples in EXAMPLES.items() for text in examples]
    try:
        vectors=await OllamaProvider(base_url=LOCAL_OLLAMA_URL).embed(
            ['search_document: '+text for _,text in items]+['search_query: '+prompt],
            os.getenv('COGNISHIELD_ROUTING_EMBED_MODEL','nomic-embed-text:latest'))
        query=vectors[-1]; scores={}
        for (intent,_),vector in zip(items,vectors):
            if len(vector)!=len(query) or any(not math.isfinite(x) for x in vector+query): return None
            denominator=math.sqrt(sum(x*x for x in vector)*sum(x*x for x in query))
            score=sum(x*y for x,y in zip(vector,query))/denominator if denominator else 0
            scores[intent]=max(scores.get(intent,-1),score)
        ranked=sorted(scores.items(),key=lambda item:item[1],reverse=True)
        intent,score=ranked[0]; margin=score-ranked[1][1]
        if score<0.57 or margin<0.055: return None
        domains=[]
        if intent.startswith('network_'):
            domain=intent.removeprefix('network_')
            domains=['inventory','topology','telemetry','syslog','incidents','configuration'] if domain=='investigation' else [domain]
            intent='network'
        return {'intent':intent,'domains':domains,'score':round(score,3),'margin':round(margin,3)}
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        return None
