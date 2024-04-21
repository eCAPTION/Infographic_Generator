import os
import json
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

from ecaption_utils.kafka.faust import get_faust_app, initialize_topics, FaustApplication, get_error_handler
from ecaption_utils.kafka.topics import Topic, get_event_type

from util import *

# Constants
NUM_LABEL = 5
CANVAS_HEIGHT, CANVAS_WIDTH = 297, 210

load_dotenv()
broker_url = os.environ.get("KAFKA_BROKER_URL")
port = os.environ.get("NEWS_EMBEDDING_SERVICE")
bootstrap_server = os.environ.get("BOOTSTRAP_SERVER")
print(broker_url, port, bootstrap_server)
app = get_faust_app(FaustApplication.InfographicGeneration, broker_url=broker_url, port=port)
topics = initialize_topics(app, [Topic.INFORMATION_QUERYING_RESULTS, Topic.ADD_INSTRUCTION, Topic.DELETE_INSTRUCTION, Topic.NEW_INFOGRAPHIC, Topic.MODIFIED_INFOGRAPHIC, Topic.MOVE_INSTRUCTION])

handle_error = get_error_handler(app)

@app.task
async def send_new_article_topic():
    topic = Topic.INFORMATION_QUERYING_RESULTS
    Event = get_event_type(topic)
    event = Event(
         request_id=0,
  url="https://www.straitstimes.com/world/united-states/baltimore-disaster-the-city-that-lost-a-bridge-looks-uncertainly-to-its-future",
  title="Baltimore disaster: The city that lost a bridge looks uncertainly to its future",
  description="The iconic 47-year-old bridge was more than a crucial transport node for its residents. Read more at straitstimes.com.",
  image="https://static1.straitstimes.com.sg/s3fs-public/styles/large30x20/public/articles/2024/03/28/HZBALTIMORE280324.jpg?VersionId\u003dqoLjQAdXN0u9kFjBXm4YYpSQfAxXq7A5",
  related_articles=[
    {
      "url": "https://www.straitstimes.com/singapore/slight-dip-in-cpf-interest-rates-for-special-medisave-and-retirement-accounts-in-q2",
      "title": "Slight dip in CPF interest rate to 4.05% for Special, MediSave and Retirement accounts in Q2",
      "image": "https://static1.straitstimes.com.sg/s3fs-public/styles/large30x20/public/articles/2024/03/12/IMGyaohui-docpf11-881711994A8EM.jpg",
      "description": "The interest rate was 4.08% a year in the first quarter of 2024. Read more at straitstimes.com.",
      "similarity": 77.675316
    }
  ],
  related_facts=[
    "Great Baltimore Fire is significant event of Baltimore",
    "United States of America is country of Baltimore",
    "United States of America is country of Chicago",
    "United States of America is country of Francis Scott Key Bridge",
    "United States of America is located in the administrative territorial entity of Maryland",
    "United States of America is country of Maryland",
    "United States of America is capital of of Washington, D.C.",
    "United States of America is country of Washington, D.C.",
    "United States of America is country of citizenship of Horatio Earle",
    "Washington, D.C. is headquarters location of American Road and Transportation Builders Association",
    "Horatio Earle is founded by of American Road and Transportation Builders Association",
    "United States of America is country of National Bridge Inventory",
    "United States of America is located in the administrative territorial entity of New Jersey",
    "United States of America is country of New Jersey",
    "United States of America is located in the administrative territorial entity of New York",
    "United States of America is country of New York",
    "United States of America is located in the administrative territorial entity of Georgia",
    "United States of America is country of Georgia",
    "United States of America is located in the administrative territorial entity of Pennsylvania",
    "United States of America is country of Pennsylvania",
    "United States of America is located in the administrative territorial entity of Virginia",
    "United States of America is country of Virginia",
    "United States of America is country of citizenship of Edgar Allan Poe",
    "United States of America is country for sport of Michael Phelps",
    "United States of America is country of citizenship of Michael Phelps",
    "United States of America is country of Visa Inc.",
    "Visa Inc. is sponsor of Olympic Games",
    "United States of America is country of citizenship of Nancy Pelosi"
  ],
  adjlist= {
    "2748733": [],
    "754452": [],
    "377595": [],
    "14290457": [],
    "2688414": [],
    "30": [],
    "1297": [
      [
        30,
        17
      ]
    ],
    "5092": [
      [
        2898431,
        793
      ],
      [
        30,
        17
      ]
    ],
    "2898431": [],
    "5482413": [
      [
        30,
        17
      ]
    ],
    "1391": [
      [
        30,
        131
      ],
      [
        30,
        17
      ]
    ],
    "61": [
      [
        30,
        1376
      ],
      [
        30,
        17
      ]
    ],
    "5902654": [
      [
        30,
        27
      ]
    ],
    "4744848": [
      [
        61,
        159
      ],
      [
        5902654,
        112
      ]
    ],
    "6971123": [
      [
        30,
        17
      ]
    ],
    "1408": [
      [
        30,
        131
      ],
      [
30,
        17
      ]
    ],
    "1384": [
      [
        30,
        131
      ],
      [
        30,
        17
      ]
    ],
    "1428": [
      [
        30,
        131
      ],
      [
        30,
        17
      ]
    ],
    "1400": [
      [
        30,
        131
      ],
      [
        30,
        17
      ]
    ],
    "1370": [
      [
        30,
        131
      ],
      [
        30,
        17
      ]
    ],
    "16867": [
      [
        30,
        27
      ]
    ],
    "39562": [
      [
        30,
        1532
      ],
      [
        30,
        27
      ]
    ],
    "328840": [
      [
        30,
        17
      ]
    ],
    "5389": [
      [
        328840,
        859
      ]
    ],
    "170581": [
      [
        30,
        27
      ]
    ]
  },
    node_occurrences={
    "2748733": 1,
    "754452": 1,
    "377595": 1,
    "14290457": 1,
    "2688414": 1,
    "30": 5,
    "1297": 1,
    "5092": 4,
    "2898431": 1,
    "5482413": 1,
    "1391": 1,
    "61": 1,
    "5902654": 1,
    "4744848": 1,
    "6971123": 1,
    "1408": 1,
    "1384": 1,
    "1428": 1,
    "1400": 1,
    "1370": 1,
    "16867": 1,
    "39562": 1,
    "328840": 1,
    "5389": 1,
    "170581": 1
  }, 
  entity_labels= {
    "2748733": "Patapsco River",
    "754452": "Glen Burnie",
    "377595": "Port of Baltimore",
    "14290457": "check",
    "2688414": "Francis Scott Key Bridge",
    "30": "United States of America",
    "1297": "Chicago",
    "5092": "Baltimore",
    "2898431": "Great Baltimore Fire",
    "5482413": "Francis Scott Key Bridge",
    "1391": "Maryland",
    "61": "Washington, D.C.",
    "5902654": "Horatio Earle",
    "4744848": "American Road and Transportation Builders Association",
    "6971123": "National Bridge Inventory",
    "1408": "New Jersey",
    "1384": "New York",
    "1428": "Georgia",
    "1400": "Pennsylvania",
    "1370": "Virginia",
    "16867": "Edgar Allan Poe",
    "39562": "Michael Phelps",
    "328840": "Visa Inc.",
    "5389": "Olympic Games",
    "170581": "Nancy Pelosi"
  },
   property_labels={
    "1376": "capital of",
    "859": "sponsor",
    "131": "located in the administrative territorial entity",
    "112": "founded by",
    "17": "country",
    "793": "significant event",
    "27": "country of citizenship",
    "1532": "country for sport",
    "159": "headquarters location"
  },
    )
    await topics[topic].send(value=event)
    return "sent: {}".format(event)

@app.task
async def send_delete_article_topic():
    topic = Topic.DELETE_INSTRUCTION
    Event = get_event_type(topic)
    event = Event(
            request_id=1,
            infographic_section='knowledge_graph',
            infographic_link='https://generated-infographics.s3.ap-southeast-1.amazonaws.com/0.jpeg'
        )
    await topics[topic].send(value=event)
    return "sent: {}".format(event)

# @app.task
# async def send_add_article_topic():
#     topic = Topic.ADD_INSTRUCTION
#     Event = get_event_type(topic)   
#     event = Event(
#             request_id=2,
#             infographic_section='',
#             target_element='knowledge_graph',
#             infographic_link='https://generated-infographics.s3.ap-southeast-1.amazonaws.com/1.jpeg'
#         )
#     await topics[topic].send(value=event)
#     return "sent: {}".format(event)

# @app.task
# async def send_move_article_topic():
#     topic = Topic.MOVE_INSTRUCTION
#     Event = get_event_type(topic)
#     event = Event(
#             request_id=2,
#             target_section='related_articles',
#             reference_section='image',
#             direction='left',
#             infographic_link='https://generated-infographics.s3.ap-southeast-1.amazonaws.com/0.jpeg'
#         )
#     await topics[topic].send(value=event)
#     return "sent: {}".format(event)

if __name__ == '__main__':
    app.main()