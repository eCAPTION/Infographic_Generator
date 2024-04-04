import networkx as nx
import requests
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import json
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
import logging
import numpy as np

load_dotenv()
generation_endpoint = os.environ.get("GENERATION_ENDPOINT")

component_label_mapping = {
    'title': 0,
    'description': 0,
    'related_articles': 0,
    'related_facts': 0,
    'knowledge_graph': 3,
    'image': 4,

}

def convert_xywh_to_ltrb(bbox):
    xc, yc, w, h = bbox
    x1 = xc - w / 2
    y1 = yc - h / 2
    x2 = xc + w / 2
    y2 = yc + h / 2
    return [x1, y1, x2, y2]

def convert_plt_to_img(fig):
    """Convert a Matplotlib figure to a PIL Image and return it"""
    import io
    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    img = Image.open(buf)
    return img

def convert_keys_str_to_int(d):
    new_d = {}
    for k in d:
        new_d[int(k)] = d[k]
    return new_d

def convert_graph_to_image(adj_list, node_occurrences, entity_labels, property_labels):
    # create the graph
    DG = nx.DiGraph()
    # add nodes
    for n in node_occurrences:
        DG.add_node(n)
    # add edges
    edge_labels = {}

    for n in adj_list:
        for nbr in adj_list[n]:
            dest_node, label_id = nbr
            DG.add_edge(n, dest_node)
            edge_labels[(n, dest_node)] = property_labels[label_id]
    pos = nx.spring_layout(DG)

    # print(len([v for v in node_occurrences.values()]))
    nx.draw_networkx(DG, with_labels=True, labels=entity_labels, node_size=[v for v in node_occurrences.values()])
    nx.draw_networkx_edge_labels(DG, pos, edge_labels=edge_labels, font_color='red')
    fig = plt.gcf()
    img = convert_plt_to_img(fig)
    img.save('graph.png')
    return img

def event_to_dict(event):
    '''
    creates and returns a dict containing all event information.
    '''
    return {
        'request_id': event.request_id,
        'title': event.title,
        'description': event.description,
        'related_articles': event.related_articles,
        'related_facts': event.related_facts,
        'image': event.image,
        'adjList': event.adjlist,
        'node_occurrences': event.node_occurrences,
        'entity_labels': event.entity_labels,
        'property_labels': event.property_labels
    }

def resize_pil_image(img, width, height):
    '''
    resizes image based on aspect ratio based on min(width, height)
    then pads the rest with whitespace
    '''
    canvas = Image.new('RGB', (int(width), int(height)), color=(255,255,255))
    img_width, img_height = img.size
    img_width_height_ratio = img_width / img_height
    if height < width:
        new_size = (int(height * img_width_height_ratio), int(height))
        upper_left = (int((width - height * img_width_height_ratio) / 2), 0)
    else:
        new_size = (int(width), int(width / img_width_height_ratio))
        upper_left = (0, int((height - width / img_width_height_ratio) / 2))
    img = img.resize(new_size)

    canvas.paste(img, upper_left)
    return canvas

# Querying infographic generator endpoint
def get_generation_from_api(num_label, label):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    res = requests.post(url=generation_endpoint + '/generate', data=json.dumps({'num_label': num_label, 'label': label}), headers=headers, timeout=60)
    bboxes, labels = res.json()['results']['bbox'], res.json()['results']['label']
    return bboxes, labels

def get_edit_from_api(id_a, id_b, relation, bbox, num_label, label):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    res = requests.post(url=generation_endpoint + '/edit', data=json.dumps({'id_a': id_a, 'id_b': id_b, 'relation': relation, 'bbox': bbox, 'num_label': num_label, 'label': label}), headers=headers, timeout=60)
    bboxes, labels = res.json()['results']['bbox'], res.json()['results']['label']
    return bboxes, labels

def draw_text_on_canvas(text, color, background_color, canvas_size):
    H, W = canvas_size
    img = Image.new('RGB', (int(W), int(H)), color=background_color)
    draw = ImageDraw.Draw(img, 'RGBA')

    font_size = 100
    words = text.split()
    while font_size > 0:
        size = None
        curr_words = []
        idx = 0 # index of current word to select

        while idx < len(words):
            curr_words.append(words[idx])
            idx += 1
            l, t, r, b = draw.multiline_textbbox((0,0), ' '.join(curr_words), font_size=font_size)
            size = (1.1 * (r-l), 1.1 * (b-t))

            if size[1] > H or (idx >= len(words) and size[0] > W): # if height exceeds or all words used and length exceeds, we have to decrease font size
                break
            if size[0] > W:
                if curr_words[-1] == '\n':
                    break

                curr_words.pop()

                idx -= 1
                curr_words.append('\n')

        if idx >= len(words) and size[0] <= W and size[1] <= H:
            # stopping condition
            break
        font_size -= 1
    draw.multiline_text((0, 0), ' '.join(curr_words), fill=color, font_size=font_size)
    l, t, r, b = draw.multiline_textbbox((0,0), ' '.join(curr_words), font_size=font_size)
    return img

def create_text_section(section_header, text, canvas_size, header_ratio=0.2):
    H, W = canvas_size
    header_height= int(header_ratio * H)
    # print(header_height, W)
    body_height = H - header_height
    img = Image.new('RGB', (int(W), int(H)), color=(255,255,255))
    header_img = draw_text_on_canvas(section_header, '#1e65ff', '#ffffff', (header_height, W))
    body_img = draw_text_on_canvas(text, '#000000', '#ffffff', (body_height, W))
    img.paste(header_img, (0, 0, W, header_height))
    img.paste(body_img, (0, header_height, W, H))
    return img

def create_title_section(text, canvas_size):
    H, W = canvas_size
    text = text.upper()
    return draw_text_on_canvas(text, '#ffffff', '#1e65ff', canvas_size)


def convert_layout_to_infographic(input_dict, boxes, labels, canvas_size, title_ratio=0.15):
    '''
    the input is a dict[label_index: [values of each label element]]
    present_sections is a list of string describing the sections present
    e.g. {0: [('title', 'Trump wins election')]}
    images are represented by Pillow Image object.
    '''
    sections_to_headings = {
        'description': 'DESCRIPTION',
        'related_articles': 'RELATED ARTICLES',
        'related_facts': 'RELATED FACTS'
    }

    # extract the header to be placed at the top.
    for i, text_tup in enumerate(input_dict[0]):
        if text_tup[0] == 'title':
            break
    title_tup = input_dict[0].pop(i)


    H, W = canvas_size
    img = Image.new('RGB', (int(W), int(H)), color=(255,255,255))

    title_height = int(title_ratio * H)
    title_img = create_title_section(title_tup[1], (title_height, W))
    img.paste(title_img, (0, 0, W, title_height))

    H -= title_height

    area = [b[2] * b[3] for b in boxes]
    indices = sorted(range(len(area)), key=lambda i : area[i], reverse=True)

    for i in indices:
        bbox, label = boxes[i], labels[i]
        x1, y1, x2, y2 = convert_xywh_to_ltrb(bbox)
        x1, y1, x2, y2 = int(x1*W), int(y1*H), int(x2*W), int(y2*H)
        if label == 3 or label == 4:
            img_to_paste = resize_pil_image(input_dict[label][0][1], x2-x1, y2-y1)
            img.paste(img_to_paste, (x1, y1 + title_height, x2, y2 + title_height))
            input_dict[label].pop(0)
        else:
            # text
            text_tup = input_dict[label][0]
            text_img = create_text_section(sections_to_headings[text_tup[0]], text_tup[1], (y2 - y1, x2 - x1))
            img.paste(text_img, (x1, y1 + title_height, x2, y2 + title_height))
            input_dict[label].pop(0)
    return img

# AWS Operations
def upload_fileobj(file_object, bucket, object_name):
    """Upload a file to an S3 bucket

    :param file_obj: File object to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_fileobj(file_object, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def download_fileobj(bucket, object_name, file_object):
    """
    Download a file from S3 bucket

    :param file_name: file name to download
    :param bucket: bucket to download from
    :param object_name S3 object name
    :return True if file was succesfully downloaded, else False
    """
    s3_client = boto3.client('s3')
    try:
        response = s3_client.download_fileobj(bucket, object_name, file_object)
    except ClientError as e:
        logging.error(e)
        return False
    return True
