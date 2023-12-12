FROM python:3.10.12
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y libsodium-dev libsecp256k1-dev libgmp-dev \
    build-essential libssl-dev libffi-dev python3-dev cargo pkg-config

WORKDIR /code
COPY requirements.txt /code/
# RUN pip install "cython<3.0.0" && pip install --no-build-isolation pyyaml==6.0
# RUN pip install setuptools_rust docker-compose
RUN pip install -r requirements.txt
COPY . /code/