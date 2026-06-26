FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nginx \
    openssl \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY app/openssl-sib.cnf /etc/ssl/openssl-sib.cnf

ENV OPENSSL_CONF=/etc/ssl/openssl-sib.cnf

EXPOSE 5080 5443

ENTRYPOINT ["/app/entrypoint.sh"]
