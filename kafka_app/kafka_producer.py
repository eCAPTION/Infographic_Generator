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
topics = initialize_topics(app, [Topic.NEWS_SEARCH_RESULTS, Topic.ADD_INSTRUCTION, Topic.DELETE_INSTRUCTION, Topic.NEW_INFOGRAPHIC, Topic.MODIFIED_INFOGRAPHIC, Topic.MOVE_INSTRUCTION])

handle_error = get_error_handler(app)

# @app.task
# async def send_new_article_topic():
#     topic = Topic.NEWS_SEARCH_RESULTS
#     Event = get_event_type(topic)
#     event = Event(
#         request_id=0,
#         url='abc.com/biden',
#         title='Biden tries to turn the tables on Trump’s use of a classic political attack line',
#         description='President Joe Biden delivers remarks on lowering costs for American families, in Las Vegas, Nevada, on March 19.',
#         related_articles=['Opinion: How Joe Biden is flipping the script on Trump', 'Opinion: Which America do you choose?'],
#         image='https://www.whitehouse.gov/wp-content/uploads/2021/04/P20210303AS-1901-cropped.jpg?w=1536',
#         adjlist={0: [1], 1: [0]},
#         node_occurrences={0: 200, 1: 100},
#         entity_labels={0: 'Biden', 1: 'Trump'}
#         )
#     await topics[topic].send(value=event)
#     return "sent: {}".format(event)

# @app.task
# async def send_delete_article_topic():
#     topic = Topic.DELETE_INSTRUCTION
#     Event = get_event_type(topic)
#     event = Event(
#             request_id=1,
#             infographic_section='knowledge_graph',
#             infographic_link='https://generated-infographics.s3.ap-southeast-1.amazonaws.com/0.jpeg'
#         )
#     await topics[topic].send(value=event)
#     return "sent: {}".format(event)

@app.task
async def send_add_article_topic():
    topic = Topic.ADD_INSTRUCTION
    Event = get_event_type(topic)   
    event = Event(
            request_id=2,
            infographic_section='',
            target_element='knowledge_graph',
            infographic_link='https://generated-infographics.s3.ap-southeast-1.amazonaws.com/1.jpeg'
        )
    await topics[topic].send(value=event)
    return "sent: {}".format(event)

# @app.task
# async def send_move_article_topic():
#     topic = Topic.MOVE_INSTRUCTION
#     Event = get_event_type(topic)
#     event = Event(
#             request_id=2,
#             target_section='related_articles',
#             reference_section='knowledge_graph',
#             direction='left',
#             infographic_link='https://generated-infographics.s3.ap-southeast-1.amazonaws.com/0.jpeg'
#         )
#     await topics[topic].send(value=event)
#     return "sent: {}".format(event)

if __name__ == '__main__':
    app.main()