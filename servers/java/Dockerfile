# Stock JDK/JSSE cannot terminate an ML-DSA TLS handshake at all (see
# README) - this uses BouncyCastle's BCJSSE provider instead. JDK 21 (LTS)
# + Bouncy Castle 1.85 (bcprov/bcpkix/bctls-jdk18on), multi-stage so the
# runtime image doesn't carry the whole Maven+JDK toolchain.
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY servers/java/pom.xml .
COPY servers/java/src ./src
RUN mvn -q -B package

FROM eclipse-temurin:21-jre

ARG ML_DSA_LEVEL=44
ARG MODE=tls
ENV ML_DSA_LEVEL=${ML_DSA_LEVEL}
ENV MODE=${MODE}

WORKDIR /app
COPY --from=build /build/target/classes ./classes
COPY --from=build /build/target/lib ./lib
COPY certs/ml-dsa-${ML_DSA_LEVEL} /certs/ml-dsa-${ML_DSA_LEVEL}

EXPOSE 8443 8444
CMD if [ "$MODE" = "mtls" ]; then java -cp classes:lib/* com.pqcpoc.MtlsServer; else java -cp classes:lib/* com.pqcpoc.TlsServer; fi
