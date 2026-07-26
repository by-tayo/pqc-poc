package com.pqcpoc;

import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLServerSocket;
import javax.net.ssl.SSLSession;
import javax.net.ssl.SSLSocket;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;

/** Bare TLS 1.3 server, server-auth only - no HTTP layer. */
public class TlsServer {
    private static final String CERT_DIR = "/certs/ml-dsa-" + System.getenv().getOrDefault("ML_DSA_LEVEL", "44");
    private static final int PORT = Integer.parseInt(System.getenv().getOrDefault("PORT", "8443"));

    public static void main(String[] args) throws Exception {
        CertUtil.registerProviders();
        CertUtil.setSignatureSchemes();

        KeyStore keyStore = CertUtil.buildKeyStore(CERT_DIR + "/server.pem", CERT_DIR + "/server.key");
        KeyManagerFactory kmf = KeyManagerFactory.getInstance("PKIX", "BCJSSE");
        kmf.init(keyStore, CertUtil.KEYSTORE_PASSWORD);

        SSLContext sslContext = SSLContext.getInstance("TLS", "BCJSSE");
        sslContext.init(kmf.getKeyManagers(), null, null);

        SSLServerSocket serverSocket = (SSLServerSocket) sslContext.getServerSocketFactory()
                .createServerSocket(PORT, 50, InetAddress.getByName("0.0.0.0"));
        System.out.println("TLS server (server-auth only) listening on :" + PORT);

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
        System.out.println("handshake OK with " + socket.getRemoteSocketAddress()
                + ": " + session.getProtocol() + " " + session.getCipherSuite());

        socket.setSoTimeout(5000);
        InputStream in = socket.getInputStream();
        OutputStream out = socket.getOutputStream();
        byte[] buf = new byte[4096];
        in.read(buf);
        // Single write so this becomes one TLS record - a client that reads
        // only once (openssl s_client -quiet, curl) needs it all in one shot.
        out.write("HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"
                .getBytes(StandardCharsets.UTF_8));
        out.flush();
    }
}
