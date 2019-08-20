FROM python:3.7-alpine3.9

MAINTAINER thanh <thanh@clgt.vn>

RUN apk update && apk add tzdata &&\
    cp /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime &&\
    echo "Asia/Ho_Chi_Minh" > /etc/timezone &&\
    apk del tzdata && rm -rf /var/cache/apk/*

COPY requirements.txt requirements.txt
RUN apk add --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    && pip install cryptography==2.2.2 \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps

ENV APP_DIR /app
WORKDIR ${APP_DIR}

ADD VERSION .
COPY . .

RUN chmod a+x ./start.sh

# exectute start up script
ENTRYPOINT ["./start.sh"]
