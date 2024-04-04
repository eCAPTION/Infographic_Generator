import os
import sys
import traceback
from joblib import load

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.logger import logger
from fastapi.encoders import jsonable_encoder
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import torch

from schema import *
from generate_custom_const import *
from exception_handler import validation_exception_handler, python_exception_handler

PRETRAINED_PTH = 'pretrained/layoutganpp_magazine.pth.tar'

app = FastAPI(
    title='Infographic Generator',
    description='generates and apply constraints on infographics'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ['*'],
    allow_methods = ['*'],
    allow_headers = ['*']
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, python_exception_handler)

@app.post('/generate', 
    response_model=ModelResponse,
    responses={422: {'model': ErrorResponse}, 500: {'model': ErrorResponse}}
    )
def do_generate(request: Request, body: GenerateInput):
    # generate given some input labels
    logger.info('generate API called')

    (bbox, label) = generate_bbox_beautify(PRETRAINED_PTH, body.label, body.num_label)

    logger.info('boxes successfully generated')

    results = {
        'bbox': bbox,
        'label': label
    }

    return {
        'error': False,
        'results': results
    }

@app.post('/edit',
    response_model=ModelResponse,
    responses={422: {'model': ErrorResponse}, 500: {'model': ErrorResponse}}
    )
def do_edit(request: Request, body: EditInput):
    # generate given some input labels
    logger.info('generate API called')

    (bbox, label) = generate_bbox_relation(PRETRAINED_PTH, body.id_a, body.id_b, body.relation, body.bbox, body.label, body.num_label)

    logger.info('boxes successfully generated')

    results = {
        'bbox': bbox,
        'label': label
    }

    return {
        'error': False,
        'results': results
    }

if __name__ == '__main__':
    uvicorn.run('main:app', host='127.0.01', port=8080, reload=True)