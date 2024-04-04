FROM python:3.11.1-slim

COPY . /usr/app

WORKDIR /usr/app

RUN pip3 install -r requirements.txt

RUN ln -s libcrypto.so.1.1 /usr/lib/libcrypto.so

CMD ["kopf", "run", "--namespace", "axis", "--namespace", "argo", "src/main.py"]