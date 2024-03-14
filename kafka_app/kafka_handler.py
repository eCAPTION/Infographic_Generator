import os
import copy
import json
import requests
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
present_sections: list[str],
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
CANVAS_HEIGHT, CANVAS_WIDTH = 594, 420
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

app = get_faust_app(FaustApplication.InfographicGeneration, broker_url=broker_url, port=port)
topics = initialize_topics(app, [Topic.NEWS_SEARCH_RESULTS, Topic.ADD_INSTRUCTION, Topic.DELETE_INSTRUCTION, Topic.NEW_INFOGRAPHIC, Topic.MODIFIED_INFOGRAPHIC])

handle_error = get_error_handler(app)

@app.agent(topics[Topic.NEWS_SEARCH_RESULTS])
async def handle_infographic_generation(event_stream):
    async for event in event_stream:
        request_id = event.request_id
        title = event.title
        desc = event.description
        related_articles = event.related_articles
        texts = [('title', title), ('description', desc)]
        for article in related_articles:
            texts.append(('related_articles', article))

        img_url = event.image
        res = requests.get(img_url)
        im = Image.open(BytesIO(res.content))
        imgs = [('image', im)]

        # knowledge subgraph information
        adj_list = convert_keys_str_to_int(event.adjlist)
        node_occurrences = convert_keys_str_to_int(event.node_occurrences) # node "importance" values
        entity_labels = convert_keys_str_to_int(event.entity_labels)

        graph_im = convert_graph_to_image(adj_list, node_occurrences, entity_labels) # im is a Pillow Image object
        graphs = [('knowledge_graph', graph_im)]

        # do the infographic generation here to obtain img url
        label = []
        input_dict = {0: texts, 1: imgs, 2: graphs}
        present_sections = [k for k in component_label_mapping.keys()]
        for k in input_dict:
            for _ in range(len(input_dict[k])):
                label.append(k)
        print('Getting infographic layout...')
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
        layout_dict['present_sections'] = present_sections
        infographic_img = convert_layout_to_infographic(input_dict, gen_bbox, gen_label, (CANVAS_HEIGHT, CANVAS_WIDTH))
        
        # save image and layout data to stream
        img_bytes = BytesIO()
        infographic_img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        json_layout_data = json.dumps(layout_dict)
        json_layout_bytes = BytesIO(json_layout_data.encode('utf-8'))
        
        # upload stream to s3 bucket
        print('Uploading infographic...')
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
        event = Event(infographic_link=url, request_id=str(request_id))
        await topics[topic].send(value=event)

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
        present_sections = layout_dict['present_sections']

        # remove infographic section from input dict
        present_sections.remove(infographic_section)

        # update label after removing section
        label = []
        for k in component_label_mapping.keys():
            if k in present_sections:
                label.append(component_label_mapping[k])


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
        layout_dict['present_sections'] = present_sections
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
        event = Event(new_infographic_link=url, request_id=str(request_id))
        await topics[topic].send(value=event)

        
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
        present_sections = layout_dict['present_sections']
        
        # check if target element already exists
        if target_element in present_sections:
            await handle_error(
                event.request_id,
                error_type=FaustApplication.InfographicGeneration,
                error_message='Target element already exists'
            )
        
        for i in range(len(present_sections)):
            if list(component_label_mapping.keys()).index(present_sections[i]) >= list(component_label_mapping.keys()).index(target_element):
                present_sections.insert(i-1, target_element)
                break
        # update label after adding target element
        label = []
        for k in component_label_mapping.keys():
            if k in present_sections:
                label.append(component_label_mapping[k])
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
        layout_dict['present_sections'] = present_sections
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
        event = Event(new_infographic_link=url, request_id=str(request_id))
        await topics[topic].send(value=event)
        