import os
import json
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

from ecaption_utils.kafka.faust import get_faust_app, initialize_topics, FaustApplication, get_error_handler
from ecaption_utils.kafka.topics import Topic, get_event_type

from util import *

'''
metadata for each infographic
{
label: list[int],
input_dict: dict[int, list[tuple(str, str)]] (component_name, content)
bbox: list[list[int]],
request_id: int,
title: str,
desc: str,
related_articles: str,
image: str,
adj_list: dict[int, list[int]],
node_occurences: dict[int, int],
entity_labels = dict[int, str]
}
'''

# Constants
NUM_LABEL = 5
CANVAS_HEIGHT, CANVAS_WIDTH = 297, 210
GENERATION_ENDPOINT = 'https://infographic-generator-106858723129.herokuapp.com'
INFOGRAPHIC_URL = 'https://generated-infographics.s3.ap-southeast-1.amazonaws.com'
BUCKET_NAME = 'generated-infographics'

# component_id_mapping = {
#     'title': 0,
#     'header': 1,
#     'related_articles': 2,
#     'image': 3,
#     'knowledge_graph': 4
# }
component_label_mapping = {
    'title': 0,
    'header': 0,
    'related_articles': 0,
    'image': 1,
    'knowledge_graph': 2
}
load_dotenv()
broker_url = os.environ.get("KAFKA_BROKER_URL")
port = os.environ.get("GATEWAY_SERVICE_PORT")
bootstrap_server = os.environ.get("BOOTSTRAP_SERVER")

app = get_faust_app(FaustApplication.Chatbot, broker_url=broker_url, port=port)
topics = initialize_topics(app, [Topic.NEWS_SEARCH_RESULTS, Topic.ADD_INSTRUCTION, Topic.DELETE_INSTRUCTION, Topic.NEW_INFOGRAPHIC, Topic.MODIFIED_INFOGRAPHIC])

handle_error = get_error_handler(app)

@app.agent(topics[Topic.NEWS_SEARCH_RESULTS])
async def handle_infographic_generation(event_stream):
    async for event in event_stream:
        request_id = event.request_id
        title = event.title
        desc = event.description
        related_articles = event.related_articles
        texts = [('title', title), ('description', desc), ('related_articles', related_articles)]

        img_url = event.image
        im = Image.open(img_url)
        imgs = [('image', im)]

        # knowledge subgraph information
        adj_list = event.adjList
        node_occurences = event.node_occurences # node "importance" values
        entity_labels = event.entity_labels

        graph_im = convert_graph_to_image(adj_list, node_occurences, entity_labels) # im is a Pillow Image object
        graphs = [('knowledge_graph', graph_im)]

        # do the infographic generation here to obtain img url
        label = []
        input_dict = {0: texts, 1: imgs, 2: graphs}
        for k in input_dict:
            for _ in range(len(input_dict[k])):
                label.append(k)

        try:
            gen_bbox, gen_label = get_generation_from_api(NUM_LABEL, label)
        except Exception as e:
            await handle_error(
                event.request_id,
                error_type=FaustApplication.InfographicGeneration,
                error_message='Error while access infographic generation API: ' + str(e)
            )
            continue

        # stores information relevant to this infographic layout
        layout_dict = event_to_dict(event) 
        layout_dict['bbox'] = gen_bbox
        layout_dict['label'] = gen_label
        layout_dict['input_dict'] = input_dict
        infographic_img = convert_layout_to_infographic(input_dict, gen_bbox, gen_label, (CANVAS_HEIGHT, CANVAS_WIDTH))
        
        # save image and layout data to stream
        img_bytes = BytesIO()
        infographic_img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        json_layout_data = json.dumps(layout_dict)
        json_layout_bytes = BytesIO(json_layout_data.encode('utf-8'))
        
        # upload stream to s3 bucket
        img_success = upload_fileobj(img_bytes, BUCKET_NAME, '{}.jpeg'.format(str(request_id)))
        json_success = upload_fileobj(json_layout_bytes, BUCKET_NAME, '{}.json'.format(str(request_id)))
        if not (img_success and json_success):
            await handle_error(
                event.request_id,
                error_type=FaustApplication.InfographicGeneration,
                error_message='Error while uploading to S3: ' + str(e)
            )
            continue
        # send the url back
        url = INFOGRAPHIC_URL + '/' + str(request_id)
        topic = Topic.NEW_INFOGRAPHIC
        Event = get_event_type(topic)
        await topics[topic].send(infographic_link=url, request_id=str(request_id))

@app.agent(topics[Topic.DELETE_INSTRUCTION])
async def handle_delete_instruction(event_stream):
    async for event in event_stream:
        request_id = event.request_id
        infographic_link = event.infographic_link
        infographic_section = event.infographic_section

        layout_object_name = infographic_link.split('/')[1] + '.json'
        json_file_in_mem = BytesIO() 

        # do the infographic generation here to obtain img url
        download_fileobj(BUCKET_NAME, layout_object_name, json_file_in_mem)
        json_file_in_mem.seek(0)

        downloaded_json_data = json_file_in_mem.read()
        layout_dict = json.loads(downloaded_json_data)
        label = layout_dict['label'] 
        input_dict = {}
        for k in layout_dict['input_dict']:
            input_dict[int(k)] = layout_dict['input_dict'][k]

        # remove infographic section from input dict
        label_of_delete_section = component_label_mapping[infographic_section]
        tup_dict = dict(input_dict[label_of_delete_section])
        tup_dict.pop(infographic_section)
        input_dict[label_of_delete_section] = list(tuple(tup_dict.items()))

        # update label after removing section
        label = []
        for k in layout_dict:
            for _ in input_dict[k]:
                label.append(k)


        # get new layout
        try:
            gen_bbox, gen_label = get_generation_from_api(NUM_LABEL, label)
        except Exception as e:
            await handle_error(
                event.request_id,
                error_type=FaustApplication.InfographicGeneration,
                error_message='Error while access infographic generation API: ' + str(e)
            )
            continue

        infographic_img = convert_layout_to_infographic(input_dict, gen_bbox, gen_label, (CANVAS_HEIGHT, CANVAS_WIDTH))
        # update layout dict
        layout_dict['label'] = label
        layout_dict['input_dict'] = input_dict
        layout_dict['bbox'] = gen_bbox

        # save image data to stream
        img_bytes = BytesIO()
        infographic_img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        json_layout_data = json.dumps(layout_dict)
        json_layout_bytes = BytesIO(json_layout_data.encode('utf-8'))
        # upload stream to s3 bucket
        img_success = upload_fileobj(img_bytes, BUCKET_NAME, '{}.jpeg'.format(str(request_id)))
        json_success = upload_fileobj(json_layout_bytes, BUCKET_NAME, '{}.json'.format(str(request_id)))
        if not (img_success and json_success):
            await handle_error(
                event.request_id,
                error_type=FaustApplication.InfographicGeneration,
                error_message='Error while uploading to S3: ' + str(e)
            )
            continue
        # send the url back
        url = INFOGRAPHIC_URL + '/' + str(request_id)
        topic = Topic.MODIFIED_INFOGRAPHIC
        Event = get_event_type(topic)
        await topics[topic].send(infographic_link=url, request_id=str(request_id))

        
@app.agent(topics[Topic.ADD_INSTRUCTION])
async def handle_add_instruction(event_stream):
    async for event in event_stream:
        request_id = event.request_id
        infographic_link = event.infographic_link
        target_element = event.target_element
        
        layout_object_name = infographic_link.split('/')[1] + '.json'
        json_file_in_mem = BytesIO() 

        # do the infographic generation here to obtain img url

        # get metadata of existing layout
        download_fileobj(BUCKET_NAME, layout_object_name, json_file_in_mem)
        json_file_in_mem.seek(0)

        downloaded_json_data = json_file_in_mem.read()
        layout_dict = json.loads(downloaded_json_data)
        input_dict = {}
        for k in layout_dict['input_dict']:
            input_dict[int(k)] = layout_dict['input_dict'][k]
        
        
        # check if target element already exists
        target_element_exists = False
        for k in input_dict:
            for v in input_dict[k]:
                if v[0] == target_element:
                    target_element_exists = True
        if target_element_exists:
            await handle_error(
                event.request_id,
                error_type=FaustApplication.InfographicGeneration,
                error_message='Target element already exists'
            )
        
        target_element_label = component_label_mapping[target_element]
        input_dict[target_element_label].append((target_element, layout_dict[target_element]))
        # update label after adding target element
        label = []
        for k in layout_dict:
            for _ in input_dict[k]:
                label.append(k)
        # get new layout
        try:
            gen_bbox, gen_label = get_generation_from_api(NUM_LABEL, label)
        except Exception as e:
            await handle_error(
                event.request_id,
                error_type=FaustApplication.InfographicGeneration,
                error_message='Error while access infographic generation API: ' + str(e)
            )
            continue

        infographic_img = convert_layout_to_infographic(input_dict, gen_bbox, gen_label, (CANVAS_HEIGHT, CANVAS_WIDTH))
        # update layout dict
        layout_dict['label'] = label
        layout_dict['input_dict'] = input_dict
        layout_dict['bbox'] = gen_bbox

        # save image data to stream
        img_bytes = BytesIO()
        infographic_img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        json_layout_data = json.dumps(layout_dict)
        json_layout_bytes = BytesIO(json_layout_data.encode('utf-8'))

        # upload stream to s3 bucket
        img_success = upload_fileobj(img_bytes, BUCKET_NAME, '{}.jpeg'.format(str(request_id)))
        json_success = upload_fileobj(json_layout_bytes, BUCKET_NAME, '{}.json'.format(str(request_id)))
        if not (img_success and json_success):
            await handle_error(
                event.request_id,
                error_type=FaustApplication.InfographicGeneration,
                error_message='Error while uploading to S3: ' + str(e)
            )
            continue
        # send the url back
        url = INFOGRAPHIC_URL + '/' + str(request_id)
        topic = Topic.MODIFIED_INFOGRAPHIC
        Event = get_event_type(topic)
        await topics[topic].send(infographic_link=url, request_id=str(request_id))
        