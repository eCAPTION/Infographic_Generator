#!/bin/bash
gunicorn -w ${WORKERS:=2} \
  -t ${TIMEOUT:=300} \
  -b 0.0.0.0:8000 \
  -k uvicorn.workers.UvicornWorker \
  main:app
