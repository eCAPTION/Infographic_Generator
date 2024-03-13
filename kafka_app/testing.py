import requests
import json

NUM_LABEL = 5
GENERATION_ENDPOINT = 'https://infographic-generator-106858723129.herokuapp.com'

label=[0,0,1,1]

headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
res = requests.post(url=GENERATION_ENDPOINT + '/generate', data=json.dumps({'num_label': NUM_LABEL, 'label': label}), headers=headers, timeout=60)

bboxes, labels = res.json()['results']['bbox'], res.json()['results']['label']
print(bboxes, labels)