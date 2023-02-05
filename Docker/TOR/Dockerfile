#https://nabarun.dev/posts/running-tor-proxy-with-docker/
FROM alpine:latest
RUN apk update && apk upgrade && apk add tor

COPY Docker/TOR/torrc /etc/tor/torrc
RUN chown -R tor /etc/tor

USER tor
ENTRYPOINT ["tor"]

CMD ["-f", "/etc/tor/torrc"]