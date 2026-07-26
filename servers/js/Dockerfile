# Node 22 bundles OpenSSL 3.5.7 internally - handles ML-DSA natively. Note:
# apt-get install openssl in this image would pull Debian bookworm's much
# older system package, which can't parse these certs - don't rely on it,
# validate this server from outside the container instead (see README).
FROM node:22-slim

ARG ML_DSA_LEVEL=44
ARG MODE=tls
ENV ML_DSA_LEVEL=${ML_DSA_LEVEL}
ENV MODE=${MODE}

WORKDIR /app
COPY servers/js/*.js ./
COPY certs/ml-dsa-${ML_DSA_LEVEL} /certs/ml-dsa-${ML_DSA_LEVEL}

EXPOSE 8443 8444
CMD if [ "$MODE" = "mtls" ]; then node mtls_server.js; else node tls_server.js; fi
