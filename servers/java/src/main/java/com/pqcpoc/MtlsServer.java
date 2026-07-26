package com.pqcpoc;

import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLServerSocket;
import javax.net.ssl.SSLSession;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.TrustManagerFactory;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.cert.X509Certificate;

/** TLS 1.3 server that requires and verifies a client certificate. */
public class MtlsServer {
    private static final String CERT_DIR = "/certs/ml-dsa-" + System.getenv().getOrDefault("ML_DSA_LEVEL", "44");
    private static final int PORT = Integer.parseInt(System.getenv().getOrDefault("PORT", "8444"));

    public static void main(String[] args) throws Exception {
        CertUtil.registerProviders();
        CertUtil.setSignatureSchemes();

        KeyStore keyStore = CertUtil.buildKeyStore(CERT_DIR + "/server.pem", CERT_DIR + "/server.key");
        KeyManagerFactory kmf = KeyManagerFactory.getInstance("PKIX", "BCJSSE");
        kmf.init(keyStore, CertUtil.KEYSTORE_PASSWORD);

        KeyStore trustStore = CertUtil.buildTrustStore(CERT_DIR + "/ca-chain.pem");
        TrustManagerFactory tmf = TrustManagerFactory.getInstance("PKIX", "BCJSSE");
        tmf.init(trustStore);

        SSLContext sslContext = SSLContext.getInstance("TLS", "BCJSSE");
        sslContext.init(kmf.getKeyManagers(), tmf.getTrustManagers(), null);

        SSLServerSocket serverSocket = (SSLServerSocket) sslContext.getServerSocketFactory()
                .createServerSocket(PORT, 50, InetAddress.getByName("0.0.0.0"));
        serverSocket.setNeedClientAuth(true);
        System.out.println("mTLS server (client cert required) listening on :" + PORT);

        while (true) {
            SSLSocket socket = (SSLSocket) serverSocket.accept();
            try {
                handle(socket);
            } catch (IOException e) {
                System.out.println("connection FAILED with " + socket.getRemoteSocketAddress() + ": " + e.getMessage());
            } finally {
                socket.close();
            }
        }
    }

    private static void handle(SSLSocket socket) throws IOException {
        socket.startHandshake();
        SSLSession session = socket.getSession();
        X509Certificate clientCert = (X509Certificate) session.getPeerCertificates()[0];
        System.out.println("handshake OK with " + socket.getRemoteSocketAddress()
                + ": " + session.getProtocol() + " " + session.getCipherSuite()
                + " client_cn=" + CertUtil.extractCn(clientCert));

        socket.setSoTimeout(5000);
        InputStream in = socket.getInputStream();
        OutputStream out = socket.getOutputStream();
        byte[] buf = new byte[4096];
        in.read(buf);
        out.write("HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"
                .getBytes(StandardCharsets.UTF_8));
        out.flush();
    }
}
