FROM willfarrell/crontab

RUN apk add --no-cache \
    python3 \
    python3-dev \
    && pip3 install --upgrade pip setuptools

WORKDIR /app

COPY requirement.txt requirement.txt
RUN pip3 install -r requirement.txt

COPY . /app

COPY config.json ${HOME_DIR}/