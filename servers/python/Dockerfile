# python:3.13-slim-trixie ships OpenSSL 3.5.6 - native ML-DSA support, no
# extra provider needed. Host OpenSSL is almost certainly older; this image
# is why the server runs in Docker at all.
FROM python:3.13-slim-trixie

ARG ML_DSA_LEVEL=44
ARG MODE=tls
ENV ML_DSA_LEVEL=${ML_DSA_LEVEL}
ENV MODE=${MODE}

WORKDIR /app
COPY servers/python/*.py ./
# Only this level's cert/key go into the image - not the other two.
COPY certs/ml-dsa-${ML_DSA_LEVEL} /certs/ml-dsa-${ML_DSA_LEVEL}

EXPOSE 8443 8444
CMD if [ "$MODE" = "mtls" ]; then python3 mtls_server.py; else python3 tls_server.py; fi
