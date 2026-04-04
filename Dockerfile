FROM ubuntu:24.04

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y python3 python3-venv python3-pip ffmpeg proxychains4 curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN python3 -m venv venv

RUN . venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir spotdl

RUN chmod +x restart_spotseek.sh restart_spotseek_queue_handler.sh

RUN echo "dynamic_chain" > /etc/proxychains4.conf && \
    echo "proxy_dns" >> /etc/proxychains4.conf && \
    echo "socks5 127.0.0.1 1080" >> /etc/proxychains4.conf

EXPOSE 3006

CMD ["/bin/bash", "-c", "./restart_spotseek.sh && ./restart_spotseek_queue_handler.sh && tail -f /dev/null"]