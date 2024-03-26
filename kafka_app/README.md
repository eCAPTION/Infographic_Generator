## Kafka Handler for Infographic Generator

### Setup
Create a Python virtual environment (Python 3.9) and activate.
```
virtualenv -p /path/to/python39 venv
source venv/bin/activate
```
Pip install from requirements.txt
```
pip install -r requirements.txt
```
Run the faust worker for `kafker_handler.py`
```
faust -A kafka_handler worker -l info
```