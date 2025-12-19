FROM python:latest

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
  && python -m pip install --no-cache-dir -r /app/requirements.txt \
  && python -c "import runpod, requests, websocket; print('deps_ok')"

COPY handler.py /app/handler.py

RUN python -c "import pathlib; p=pathlib.Path('/app/handler.py'); print('handler_exists=' + str(p.exists()))"

CMD ["python", "-u", "handler.py"]


