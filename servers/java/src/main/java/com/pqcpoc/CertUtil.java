package com.pqcpoc;

import org.bouncycastle.asn1.pkcs.PrivateKeyInfo;
import org.bouncycastle.cert.X509CertificateHolder;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.bouncycastle.jsse.provider.BouncyCastleJsseProvider;
import org.bouncycastle.openssl.PEMParser;
import org.bouncycastle.openssl.jcajce.JcaPEMKeyConverter;

import java.io.FileReader;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.Security;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;

/**
 * PEM loading + BCFKS keystore assembly shared by the TLS/mTLS server and
 * client entry points. Stock JSSE (SunJSSE) doesn't recognize ML-DSA as a
 * certificate auth scheme, so everything here goes through BC's own
 * provider (BC) and JSSE-compatible TLS provider (BCJSSE) instead.
 */
final class CertUtil {
    static final char[] KEYSTORE_PASSWORD = "pqc-poc".toCharArray();

    private CertUtil() {
    }

    static void registerProviders() {
        Security.addProvider(new BouncyCastleProvider());
        Security.addProvider(new BouncyCastleJsseProvider());
    }

    // BCJSSE doesn't advertise ML-DSA's still-draft TLS signature-scheme
    // codepoints by default - has to be set before any SSLContext is created.
    static void setSignatureSchemes() {
        String schemes = "mldsa44,mldsa65,mldsa87,ecdsa_secp256r1_sha256,rsa_pss_rsae_sha256";
        System.setProperty("jdk.tls.server.SignatureSchemes", schemes);
        System.setProperty("jdk.tls.client.SignatureSchemes", schemes);
    }

    static PrivateKey loadPrivateKey(String path) throws Exception {
        try (PEMParser parser = new PEMParser(new FileReader(path))) {
            PrivateKeyInfo info = (PrivateKeyInfo) parser.readObject();
            return new JcaPEMKeyConverter().setProvider("BC").getPrivateKey(info);
        }
    }

    static X509Certificate loadCertificate(String path) throws Exception {
        try (PEMParser parser = new PEMParser(new FileReader(path))) {
            X509CertificateHolder holder = (X509CertificateHolder) parser.readObject();
            return new JcaX509CertificateConverter().setProvider("BC").getCertificate(holder);
        }
    }

    /** In-memory BCFKS keystore holding one identity: cert + private key. */
    static KeyStore buildKeyStore(String certPath, String keyPath) throws Exception {
        PrivateKey key = loadPrivateKey(keyPath);
        X509Certificate cert = loadCertificate(certPath);
        KeyStore keyStore = KeyStore.getInstance("BCFKS", "BC");
        keyStore.load(null, KEYSTORE_PASSWORD);
        keyStore.setKeyEntry("identity", key, KEYSTORE_PASSWORD, new Certificate[]{cert});
        return keyStore;
    }

    /** In-memory BCFKS keystore holding one trusted CA/cert entry. */
    static KeyStore buildTrustStore(String certPath) throws Exception {
        X509Certificate cert = loadCertificate(certPath);
        KeyStore trustStore = KeyStore.getInstance("BCFKS", "BC");
        trustStore.load(null, KEYSTORE_PASSWORD);
        trustStore.setCertificateEntry("trusted", cert);
        return trustStore;
    }

    static String extractCn(X509Certificate cert) {
        String dn = cert.getSubjectX500Principal().getName();
        for (String part : dn.split(",")) {
            if (part.startsWith("CN=")) {
                return part.substring(3);
            }
        }
        return dn;
    }
}
