from sentence_transformers import SentenceTransformer
from openai.embeddings_utils import get_embeddings, cosine_similarity
from elasticsearch import Elasticsearch
import openai
import json
import re


api_key = "your-api-key"
openai.api_key = api_key
EMBEDDING_DIMS = 768
ENCODER_BOOST = 10
headinglist = []
new_sentences = []

# Initialie the bert model to create embeddings
sentence_transformer = SentenceTransformer("sentence-transformers/multi-qa-mpnet-base-dot-v1")
# Connect to Elastic Search
try:
    es_client = Elasticsearch("http://localhost:9200", verify_certs=False, request_timeout=60)
except: 
    print("Exception Error")
# es_client = Elasticsearch("http://elasticsearch:9200", verify_certs=False, request_timeout=600)



"""//////////////////////////////////////////////// Creating index in elastic search for Property and callsdata /////////////////////////////////////////////////////////"""

def create_index(index_name) -> None:
    es_client.options(ignore_status=[400,404]).indices.delete(index=index_name)
    es_client.indices.create(
        index=index_name,
        mappings={
            "properties": {
                "embedding": {
                    "type": "dense_vector",
                    "dims": EMBEDDING_DIMS,
                },
                "Question": {
                    "type": "text",
                },
                "Response": {
                    "type": "text",
                },
            }
        }
    )

def refresh_index(index_name) -> None:
    es_client.indices.refresh(index=index_name)

"""///////////////////////////////////////////////////// ADDING VALUES TO ELASTIC SEARCH ENGINE /////////////////////////////////////////////////////////////////////////"""

def index_context(question, index_name, reply):
    
    embedding = sentence_transformer.encode(question)
    data = {
        "Question": question,
        "embedding": embedding,
        "Response": reply
    }
    
    es_client.options(max_retries=0).index(
        index=index_name,
        document=data
    )

"""//////////////////////////////////////// MACTHING THE SCORES OF CALLS WITH THE QUESTION OF THE SPECIFIED PROPERTY ////////////////////////////////////////////////////"""

def query_response(question: str, index_name: str, top_n: int):
    embedding = sentence_transformer.encode(question)
    es_result = es_client.search(
    index=index_name,
    size=top_n,
    from_=0,
    source=["Question", "Response"],
    body={
        "query": {
            "function_score": {
                "query": {
                    "match": {
                        "Question": question
                    }
                },
                "script_score": {
                    "script": {
                        "source": """
                            (cosineSimilarity(params.query_vector, 'embedding') + 1) * params.encoder_boost + _score
                        """,
                        "params": {
                            "query_vector": embedding,
                            "encoder_boost": ENCODER_BOOST
                        }
                    }
                },
                "min_score": 1500  # Specify your desired minimum score here
            }
        }
    }
)
    # print("RESULTS ____ ", es_result)
    hits = es_result["hits"]["hits"]
    clean_result = []
    for hit in hits:
        clean_result.append({
            "Question" : hit["_source"]["Question"],
            "Response": hit["_source"]["Response"],
            "score": hit["_score"],
        })
    
    return clean_result

def feedback_index() -> None:
    #  es_feed = Elasticsearch("http://localhost:9200", verify_certs=False, request_timeout=60)
     es_client.options(ignore_status=404).indices.delete(index = "feedbackindex")
     es_client.indices.create(
          index = "feedbackindex",
          mappings = {
               "properties": {
                    "embedding": {
                         "type" : "dense_vector",
                         "dims" : EMBEDDING_DIMS,
                    },
                    "Question" : {
                         "type" : "text",
                    },
                    "Response" : {
                         "type" : "text",
                    },
                    "Feedback" : {
                         "type" : "text",
                    },
                    "Suggestion" : {
                         "type" : "text",
                    }
               }
          }
     )

def feedback_index_context(question, feedback, response, suggestion) -> None:
    
    embedding = sentence_transformer.encode(question)
    data = {
        "Question": question,
        "embedding": embedding,
        "Response": response,
        "Feedback" : feedback,
        "Suggestion" : suggestion
    }
    
    es_client.options(max_retries=0).index(
        index="feedbackindex",
        document=data
    )

def feedback_query (question):
    embedding = sentence_transformer.encode(question)
    es_result = es_client.search(
    index= "feedbackindex",
    size=3,
    from_=0,
    source=["Question", "Response"],
    body={
        "query": {
            "function_score": {
                "query": {
                    "match": {
                        "Question": question
                    }
                },
                "script_score": {
                    "script": {
                        "source": """
                            (cosineSimilarity(params.query_vector, 'embedding') + 1) * params.encoder_boost + _score
                        """,
                        "params": {
                            "query_vector": embedding,
                            "encoder_boost": ENCODER_BOOST
                        }
                    }
                },
                "min_score": 3000  # Specify your desired minimum score here
            }
        }
    }
)
    # print("RESULTS ____ ", es_result)
    hits = es_result["hits"]["hits"]
    clean_result = []
    for hit in hits:
        clean_result.append({
            "Question" : hit["_source"]["Question"],
            "Response": hit["_source"]["Response"],
            "Feedback" : hit["_source"]["Feedback"],
            "Suggestion" : hit["_source"]["Suggestion"],
            "score": hit["_score"],
        })
    
    return clean_result


"""////////////////////////////////////////////////////////////// OPENAI GPT PROMPT FUNCTIONS ///////////////////////////////////////////////////////////////////////////"""

def get_info(question, response, feedback, prev_response, suggestion, city, state, country, history):
    __history = []
    for data in history:
        conversation = {
             "user": data.question,
             "assistant": data.response
        }
        __history.append(conversation)
    template = """{"response": {
                        "data": {
                            "headers": [headers for table],
                            "rows": [data in table]
                        }
                    },
                    "type": "table"}
                    {"response":{
                        "steps": [steps in list]
                    },
                    "type": "list"
                    }
                    {"response": [test response from gpt],
                    "type": "plain text"}
                    """
    if response:
        contexts = f"""You are required to answer to question (provided in double backslash) using the data(provided in the triple bacticks) that contains the replies \ 
                    of people who faced the same issues.\nAlso you have been provided with the feedback of the previous responses use them as a means to give a \
                    suitable response. And do not add anything like according to replies etc.\
                    My current location is \nCity:{city}, \nState:{state}, \nCountry{country}.
                    \nIMPORTANT INSTRUCTIONS: You are had to make a json response object in answer, wether you are generating the response in a table or \
                    list format or not the response should always be in json and identified as list or \
                    table or text(if text contains points it should be list not  text). You are not to generate an empty response. The template for json response is given as follow:{template}
                    \ndata:{response}\nquesiton:{question}\nfeedback:{feedback}\nSuggestion: {suggestion} \nprevious response: {prev_response} 
                    \nAnswer:[response in JSON]"""
        messages = [{"role": "user", "content": contexts}]
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo-16k", messages=messages, temperature = 0)
        reply = response.choices[0].message.content
    else:
        contexts = f"""You are a AI assistant for agtalk website and resolve the user quries. And give a seemless conversation flow.
                    \nMy current location is \nCity:{city}, \nState:{state}, \nCountry{country}
                    \nIMPORTANT INSTRUCTIONS: You are had to make a json response object in answer, wether you are generating the response in a table or \
                    list format or not the response should always be in json and identified as list or \ 
                    table or text(if text contains points it should be list not  text). You are not to generate an empty response. The template for json response is given as follow:{template}
                    \nHistory = {__history} \nAnswer:[response in json]"""
        messages = [{"role": "system", "content": contexts},
                    {"role": "user", "content": question}
                    ]
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo-16k", messages=messages, temperature = 0)
        reply = response.choices[0].message.content
    
    contexts = f"""
                I will provide you with the response of gpt3.5. You are required to format the response in the templates given below in Templates. If type is table then use the json with type table.
                If the response is plain text then just use the format with the type plian text.
                Templates: {template} Reply of the gpt:{reply}
                """
                
    try:
        reply = json.loads(reply)
        if reply["response"]["data"]["rows"]:
            messages = [
                {"role": "user", "content": contexts}]
            response = openai.ChatCompletion.create(model="gpt-3.5-turbo-16k", messages = messages, temperature = 0)
            # Use regular expression to find the JSON object within the text
            reply = response.choices[0].message.content
            pattern = r'```json\n(.*?)```'
            match = re.search(pattern, reply, re.DOTALL)

            pattern2 = r"```(\{.*?\})```"
            match2 = re.search(pattern2, reply, re.DOTALL)

            pattern3 =r'\{.*\}'
            match3 = re.search(pattern3, reply, re.DOTALL)
            if match:
                json_str = match.group(1)
                reply = json_str

            if match2:
                json_str = match2.group(1)
                reply = json_str
            
            if match3:
                json_str = match3.group()
                reply = json_str
            
            try:
                if "\"list\"" in reply and ("\n" in reply or "\\n" in reply) :
                    reply = json.loads(reply)
                    response_body = reply["response"]["steps"]
                    response_list = response_body.split("\n" if "\n" in response_body else "\\n")

                    response_list = [item.strip() for item in response_list if item.strip()]
                    print(response_list)
                    # Modify the JSON structure
                    json_data = {
                        "response": {
                        "steps": response_list[1:]},
                        "type": "list"
                    }
                    reply = json.dumps(json_data, indent=2)
            except: 
                reply = json.dumps(reply)
            if not "\"list\"" in reply and not "\"table\"" in reply:
                    if "\\n" in reply or "\n\n" in reply:
                        try:
                            response_text = json.loads(reply)
                            json_text = response_text["response"] + response_text["steps"]
                        except:
                            json_text = reply
                        # Split the response by "\\n" and create a list
                        response_list = json_text.split("\\n" if "\\n" in reply else "\n\n")
                        response_list = [item.split("\n") for item in response_list]
                        bool = has_nested_list(response_list)
                        if bool == True:
                            response_list = flatten_list(response_list)
                        # Remove empty strings from the list
                        response_list = [item.strip() for item in response_list if item.strip()]

                        # Modify the JSON structure
                        json_data = {
                            "response":{
                            "steps": response_list[1:]},
                            "type": "list"
                        }

                        # Serialize the modified JSON object with proper indentation
                        reply = json.dumps(json_data, indent=2)
                
            return reply
        else:
            return """{\"response\": {\n    \"data\": {\n        \"headers\": [],\n        \"rows\": [["Try Again"]]\n    }\n},\n\"type\": \"table\"}"""
    except:
        messages = [
            {"role": "user", "content": contexts}]
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo-16k", messages = messages, temperature = 0)
        # Use regular expression to find the JSON object within the text
        reply = response.choices[0].message.content
        pattern = r'```json\n(.*?)```'
        match = re.search(pattern, reply, re.DOTALL)

        pattern2 = r"```(\{.*?\})```"
        match2 = re.search(pattern2, reply, re.DOTALL)

        pattern3 =r'\{.*\}'
        match3 = re.search(pattern3, reply, re.DOTALL)
        if match:
            json_str = match.group(1)
            reply = json_str

        if match2:
            json_str = match2.group(1)
            reply = json_str
        
        if match3:
            json_str = match3.group()
            reply = json_str
        
        try:
            if "\"list\"" in reply and ("\n" in reply or "\\n" in reply) :
                reply = json.loads(reply)
                response_body = reply["response"]["steps"]
                response_list = response_body.split("\n" if "\n" in response_body else "\\n")

                response_list = [item.strip() for item in response_list if item.strip()]
                print(response_list)
                # Modify the JSON structure
                json_data = {
                    "response": {
                    "steps": response_list[1:]},
                    "type": "list"
                }
                reply = json.dumps(json_data, indent=2)
        except: 
            reply = json.dumps(reply)
        if not "\"list\"" in reply and not "\"table\"" in reply:
                if "\\n" in reply or "\n\n" in reply:
                    try:
                        response_text = json.loads(reply)
                        json_text = response_text["response"] + response_text["steps"]
                    except:
                        json_text = reply
                    # Split the response by "\\n" and create a list
                    response_list = json_text.split("\\n" if "\\n" in reply else "\n\n")
                    response_list = [item.split("\n") for item in response_list]
                    bool = has_nested_list(response_list)
                    if bool == True:
                        response_list = flatten_list(response_list)
                    # Remove empty strings from the list
                    response_list = [item.strip() for item in response_list if item.strip()]

                    # Modify the JSON structure
                    json_data = {
                        "response":{
                        "steps": response_list[1:]},
                        "type": "list"
                    }

                    # Serialize the modified JSON object with proper indentation
                    reply = json.dumps(json_data, indent=2)
            
        return reply

"""///////////////////////////////////////////////////////// TO search the elastic engine for the sementic/ embedding matching of question ///////////////////////////////"""

def elastic_search(question, city, state, country, previous_response):

        try:
                x = query_response(question, "chatbot_data", 1)
                # print(x)
                summary = x[0]['Response']
                y = feedback_query(question)
                if y[0]:
                    feedback = y[0]['Feedback']
                    response = y[0]['Response']
                    suggestion = y[9]['Suggestion']
                else:
                    feedback = ""
                    response = ""
                    suggestion = ""
                answer = get_info(question, summary, feedback, response, suggestion, city, state, country, previous_response)
        except:
                summary = None
                feedback = ""
                response = ""
                suggestion = ""
                answer = get_info(question, summary, feedback , response , suggestion, city, state, country, previous_response)

        return answer

def check_elasticsearch_data(index_name):

    # Set the number of records to retrieve
    size = 100

    # Set the initial scroll timeout
    scroll_timeout = '1m'

    # Initialize the scroll parameter
    scroll_id = None

    # Retrieve the first batch of data using the scroll API
    es_result = es_client.search(
        index=index_name,
        size=size,
        scroll=scroll_timeout,
        body={}
    )

    # Extract the scroll ID and total number of hits
    scroll_id = es_result['_scroll_id']
    total_hits = es_result['hits']['total']['value']
    print(total_hits)
    # Process and print the retrieved documents
    # while total_hits > 0:
    #     # Extract the documents from the search result
    #     documents = es_result['hits']['hits']
    #     print(len(documents))
    #     # Process each document
    #     for doc in documents:
    #         # Extract the source data from the document
    #         source_data = doc['_source']

    #         # Print the source data
    #         print(source_data)

    #     # Check if there are more results to retrieve
    #     if len(documents) < size:
    #         break

    #     # Scroll to the next batch of data
    #     es_result = es_client.scroll(
    #         scroll_id=scroll_id,
    #         scroll=scroll_timeout
    #     )

    #     # Update the scroll ID and total hits
    #     scroll_id = es_result['_scroll_id']
    #     total_hits = es_result['hits']['total']['value']

    # Clear the scroll
    es_client.clear_scroll(scroll_id=scroll_id)

def delete_documents_with_empty_embeddings(index_name):

    # Define the query to retrieve documents with empty embeddings
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "script": {
                            "script": {
                                "source": "!doc['embedding.keyword'].empty"
                            }
                        }
                    },
                    {
                        "script": {
                            "script": {
                                "source": "doc['embedding.keyword'].size() == 0"
                            }
                        }
                    }
                ]
            }
        }
    }

    # Scroll through the documents matching the query
    scroll = es_client.search(
        index=index_name,
        scroll="2m",
        size=100,
        body=query
    )

    while len(scroll['hits']['hits']) > 0:
        for document in scroll['hits']['hits']:
            document_id = document["_id"]
            # Delete each document with an empty embedding
            es_client.delete(index=index_name, id=document_id)
            print(f"Deleted document with ID: {document_id}")

        # Scroll to the next batch of data
        scroll = es_client.scroll(
            scroll_id=scroll['_scroll_id'],
            scroll='2m'
        )

def delete_all_documents(index_name):
    # Create an Elasticsearch client
    # es_client = Elasticsearch()

    # Define the delete query to delete all documents in the index
    delete_query = {
        "query": {
            "match_all": {}
        }
    }

    # Delete all documents in the index
    response = es_client.delete_by_query(
        index=index_name,
        body=delete_query,
        scroll='2m'
    )

    # Print the response
    print(f"Deleted {response['deleted']} documents from index: {index_name}")

def data_to_elasticSearch(question, reply):
        es_client = Elasticsearch("http://localhost:9200", verify_certs=False, request_timeout=60)
        question = question
        response = reply
        if not es_client.indices.exists(index="chatbot_data"):
                print("i am here!")
                create_index("chatbot_data")
        refresh_index("chatbot_data")
        index_context(question=question, index_name="chatbot_data", reply=response)


def data_to_feedback(question, feedback, response, suggestion):

    if not es_client.indices.exists(index="feedbackindex"):
            # print("i am here!")
            feedback_index()
    refresh_index("feedbackindex")
    feedback_index_context(question, feedback, response, suggestion)

    return "Feedback Indexed Successfully"

def has_nested_list(lst):
    for item in lst:
        if isinstance(item, list):
            return True
    return False

def flatten_list(nested_list):
    flattened = []
    for item in nested_list:
        if isinstance(item, list):
            flattened.extend(flatten_list(item))
        else:
            flattened.append(item)
    return flattened


