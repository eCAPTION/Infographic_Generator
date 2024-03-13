import os
import requests
from dotenv import load_dotenv
from PIL import Image

from ecaption_utils.kafka.faust import get_faust_app, initialize_topics, FaustApplication
from ecaption_utils.kafka.topics import Topic, get_event_type

from util import *

NUM_LABEL = 5
GENERATION_ENDPOINT = 'https://infographic-generator-106858723129.herokuapp.com'

load_dotenv()
broker_url = os.environ.get("KAFKA_BROKER_URL")
port = os.environ.get("GATEWAY_SERVICE_PORT")
bootstrap_server = os.environ.get("BOOTSTRAP_SERVER")

app = get_faust_app(FaustApplication.Chatbot, broker_url=broker_url, port=port)
topics = initialize_topics(app, [Topic.NEWS_SEARCH_RESULTS, Topic.ADD_INSTRUCTION, Topic.DELETE_INSTRUCTION, Topic.NEW_INFOGRAPHIC, Topic.MODIFIED_INFOGRAPHIC])

@app.agent(topics[Topic.NEWS_SEARCH_RESULTS])
async def handle_infographic_generation(event_stream):
    async for event in event_stream:
        request_id = event.request_id
        title = event.title
        desc = event.description
        related_articles = event.related_articles
        related_facts = event.related_facts

        texts = [title, desc, related_articles, related_facts]

        img_url = event.image
        # image
        im = Image.open(img_url)
        imgs = [im]

        # knowledge subgraph information
        adj_list = event.adjList
        node_occurences = event.node_occurences # node "importance" values
        entity_labels = event.entity_labels

        graph_im = convert_graph_to_image(adj_list, node_occurences, entity_labels) # im is a Pillow Image object
        graphs = [graph_im]

        # do the infographic generation here to obtain img url
        label = []
        for _ in texts:
            label.append(0)
        for _ in imgs:
            label.append(1)
        for _ in graphs:
            label.append(2)
        
        gen_bbox, gen_label = get_generation_from_api(NUM_LABEL, label)
        # send the url back 
        DUMMY_URL = 'https://assets1.cbsnewsstatic.com/hub/i/r/2011/04/13/0c9bfbe6-a643-11e2-a3f0-029118418759/thumbnail/1200x630/83017e8b1510dc4907cf08bc9f0cc814/Biden_1.png?v=b15ba9ca383d8472a236fb5b5c7ca2b3' # TODO: get the actual URL
        topic = Topic.NEW_INFOGRAPHIC
        Event = get_event_type(topic)
        await topics[topic].send(infographic_link=DUMMY_URL, request_id=request_id)

@app.agent(topics[Topic.DELETE_INSTRUCTION])
async def handle_delete_instruction(event_stream):
    async for event in event_stream:
        request_id = event.request_id
        infographic_link = event.infographic_link
        infographic_section = event.infographic_section

        # do the infographic generation here to obtain img url

        # send the url back 
        DUMMY_URL = 'https://assets1.cbsnewsstatic.com/hub/i/r/2011/04/13/0c9bfbe6-a643-11e2-a3f0-029118418759/thumbnail/1200x630/83017e8b1510dc4907cf08bc9f0cc814/Biden_1.png?v=b15ba9ca383d8472a236fb5b5c7ca2b3' # TODO: get the actual URL
        topic = Topic.NEW_INFOGRAPHIC
        Event = get_event_type(topic)
        await topics[topic].send(infographic_link=DUMMY_URL)
        
@app.agent(topics[Topic.DELETE_INSTRUCTION])
async def handle_add_instruction(event_stream):
    async for event in event_stream:
        request_id = event.request_id
        infographic_link = event.infographic_link
        target_element = event.target_element
        infographic_section = event.infographic_section
        
        # add a target element next to (right or left) existing infographic section

        # send the url back 
        DUMMY_URL = 'https://assets1.cbsnewsstatic.com/hub/i/r/2011/04/13/0c9bfbe6-a643-11e2-a3f0-029118418759/thumbnail/1200x630/83017e8b1510dc4907cf08bc9f0cc814/Biden_1.png?v=b15ba9ca383d8472a236fb5b5c7ca2b3' # TODO: get the actual URL
        topic = Topic.NEW_INFOGRAPHIC
        Event = get_event_type(topic)
        await topics[topic].send(infographic_link=DUMMY_URL)




        