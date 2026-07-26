package com.pqcpoc;

import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.TrustManagerFactory;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.KeyStore;

/** mTLS client: presents client.pem/client.key, trusts the EJBCA CA. */
public class MtlsClient {
    private static final String CERT_DIR = "/certs/ml-dsa-" + System.getenv().getOrDefault("ML_DSA_LEVEL", "44");
    private static final String HOST = System.getenv().getOrDefault("HOST", "localhost");
    private static final int PORT = Integer.parseInt(System.getenv().getOrDefault("PORT", "8444"));

    public static void main(String[] args) throws Exception {
        CertUtil.registerProviders();
        CertUtil.setSignatureSchemes();

        KeyStore trustStore = CertUtil.buildTrustStore(CERT_DIR + "/ca-chain.pem");
        TrustManagerFactory tmf = TrustManagerFactory.getInstance("PKIX", "BCJSSE");
        tmf.init(trustStore);

        KeyStore keyStore = CertUtil.buildKeyStore(CERT_DIR + "/client.pem", CERT_DIR + "/client.key");
        KeyManagerFactory kmf = KeyManagerFactory.getInstance("PKIX", "BCJSSE");
        kmf.init(keyStore, CertUtil.KEYSTORE_PASSWORD);

        SSLContext sslContext = SSLContext.getInstance("TLS", "BCJSSE");
        sslContext.init(kmf.getKeyManagers(), tmf.getTrustManagers(), null);

        try (SSLSocket socket = (SSLSocket) sslContext.getSocketFactory().createSocket(HOST, PORT)) {
            long t0 = System.nanoTime();
            socket.startHandshake();
            long t1 = System.nanoTime();
            System.out.println("handshake OK: " + socket.getSession().getProtocol()
                    + " " + socket.getSession().getCipherSuite());
            System.out.printf("handshake time: %.2f ms%n", (t1 - t0) / 1_000_000.0);

            OutputStream out = socket.getOutputStream();
            out.write("GET / HTTP/1.1\r\nHost: pqc.poc.localhost\r\n\r\n".getBytes());
            out.flush();

            InputStream in = socket.getInputStream();
            byte[] buf = new byte[4096];
            int n = in.read(buf);
            System.out.println(new String(buf, 0, n));
        }
    }
}
