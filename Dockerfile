FROM python:3.7-alpine3.9

MAINTAINER thanh <thanh@clgt.vn>

RUN apk update && apk add tzdata &&\
    cp /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime &&\ 
    echo "Asia/Ho_Chi_Minh" > /etc/timezone &&\ 
    apk del tzdata && rm -rf /var/cache/apk/*

COPY requirement.txt requirement.txt
RUN apk add --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    && pip install cryptography==2.2.2 \ 
    && pip install --no-cache-dir -r requirement.txt \
    && apk del .build-deps

COPY app.py /app/app.py
COPY clean_up_stream.py /app/clean_up_stream.py
COPY crons /etc/crontabs/root
CMD chown root:root /etc/crontabs/root
CMD ["crond", "-f"]