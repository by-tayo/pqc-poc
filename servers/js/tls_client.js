const net = require("net");
const tls = require("tls");
const fs = require("fs");

const CERT_DIR = `/certs/ml-dsa-${process.env.ML_DSA_LEVEL || "44"}`;
const HOST = process.env.HOST || "localhost";
const PORT = 8443;

const rawSocket = net.connect({ host: HOST, port: PORT }, () => {
  const t0 = process.hrtime.bigint();
  const socket = tls.connect(
    {
      socket: rawSocket,
      ca: fs.readFileSync(`${CERT_DIR}/ca-chain.pem`),
      // server.pem has no subjectAltName (EJBCA's SERVER profile doesn't carry
      // the requested dNSName through) - CN only
      checkServerIdentity: () => undefined,
    },
    () => {
      const t1 = process.hrtime.bigint();
      console.log(`handshake OK: ${socket.getProtocol()} ${socket.getCipher().standardName}`);
      console.log(`handshake time: ${(Number(t1 - t0) / 1e6).toFixed(2)} ms`);
      socket.write("GET / HTTP/1.1\r\nHost: pqc.poc.localhost\r\n\r\n");
    }
  );

  socket.on("data", (data) => {
    console.log(data.toString());
    socket.end();
  });

  socket.on("error", (err) => {
    console.error(`handshake FAILED: ${err.message}`);
    process.exitCode = 1;
  });
});

rawSocket.on("error", (err) => {
  console.error(`connection FAILED: ${err.message}`);
  process.exitCode = 1;
});
