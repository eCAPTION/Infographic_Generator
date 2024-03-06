#!/bin/bash
gunicorn -w ${WORKERS:=2} \
  -t ${TIMEOUT:=300} \
  -k uvicorn.workers.UvicornWorker \
  main:app