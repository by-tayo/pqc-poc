const tls = require("tls");
const fs = require("fs");

const CERT_DIR = `/certs/ml-dsa-${process.env.ML_DSA_LEVEL || "44"}`;
const PORT = 8444;

const server = tls.createServer(
  {
    cert: fs.readFileSync(`${CERT_DIR}/server.pem`),
    key: fs.readFileSync(`${CERT_DIR}/server.key`),
    ca: fs.readFileSync(`${CERT_DIR}/ca-chain.pem`),
    requestCert: true,
    rejectUnauthorized: true,
    minVersion: "TLSv1.3",
  },
  (socket) => {
    const client = socket.getPeerCertificate();
    console.log(
      `handshake OK with ${socket.remoteAddress}:${socket.remotePort}: ${socket.getProtocol()} ${socket.getCipher().standardName} client_cn=${client.subject && client.subject.CN}`
    );
    socket.on("data", () => {
      socket.end("HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok");
    });
  }
);

server.on("tlsClientError", (err, socket) => {
  console.error(`connection FAILED with ${socket.remoteAddress}:${socket.remotePort}: ${err.message}`);
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`mTLS server (client cert required) listening on :${PORT}`);
});
