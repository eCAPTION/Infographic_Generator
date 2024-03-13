import networkx as nx
import requests
import matplotlib.pyplot as plt
from PIL import Image
import json

GENERATION_ENDPOINT = 'https://infographic-generator-106858723129.herokuapp.com'

def convert_plt_to_img(fig):
    """Convert a Matplotlib figure to a PIL Image and return it"""
    import io
    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    img = Image.open(buf)
    return img

def convert_graph_to_image(adj_list, node_occurences, entity_labels):
    # create the graph
    DG = nx.DiGraph()
    # add nodes
    for i in range(len(node_occurences)):
        DG.add_node(i)
    
    # add edges
    for n in adj_list:
        for nbr in adj_list[n]:
            DG.add_edge(n, nbr)
    
    nx.draw_networkx(DG, with_labels=True, labels=entity_labels, node_size=node_occurences)
    fig = plt.gcf()
    img = convert_plt_to_img(fig)
    return img

def get_generation_from_api(num_label, label):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    res = requests.post(url=GENERATION_ENDPOINT + '/generate', data=json.dumps({'num_label': num_label, 'label': label}), headers=headers, timeout=60)
    bboxes, labels = res.json()['results']['bbox'], res.json()['results']['label']
    return bboxes, labels
