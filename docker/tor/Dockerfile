FROM debian:12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends tor && \
    rm -rf /var/lib/apt/lists/*

COPY torrc /etc/tor/torrc

VOLUME ["/var/lib/tor"]

EXPOSE 9050

CMD ["/usr/bin/tor", "-f", "/etc/tor/torrc"]
