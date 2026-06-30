/**
 * whatsapp-server/server.js
 * ──────────────────────────
 * Servidor Express que expone una API REST local para enviar mensajes
 * de WhatsApp usando whatsapp-web.js.
 *
 * Endpoints:
 *   GET  /estado     → estado de la conexión (qr, conectado, desconectado)
 *   POST /enviar     → envía un mensaje  { telefono, mensaje }
 *   GET  /qr         → devuelve el QR como texto ASCII (para escanear)
 *
 * Uso:
 *   node server.js
 *
 * El servidor queda escuchando en http://localhost:3001
 */

const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const express = require("express");

const app = express();
app.use(express.json());

const PORT = 3001;

// ── Estado global ─────────────────────────────────────────────────────────────
let estado = "inicializando"; // inicializando | qr_pendiente | conectado | desconectado
let qrActual = null;

// ── Cliente WhatsApp ──────────────────────────────────────────────────────────
const client = new Client({
  authStrategy: new LocalAuth({ dataPath: "./.wwebjs_auth" }),
  puppeteer: {
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-accelerated-2d-canvas",
      "--no-first-run",
      "--no-zygote",
      "--disable-gpu",
    ],
  },
});

client.on("qr", (qr) => {
  estado = "qr_pendiente";
  qrActual = qr;
  console.log("\n════════════════════════════════════════");
  console.log("  Escaneá este QR con WhatsApp en tu celular:");
  console.log("════════════════════════════════════════\n");
  qrcode.generate(qr, { small: true });
  console.log("\n(El QR también está disponible en GET /qr)\n");
});

client.on("ready", () => {
  estado = "conectado";
  qrActual = null;
  console.log("✅ WhatsApp conectado y listo para enviar mensajes.");
});

client.on("authenticated", () => {
  console.log("🔐 Autenticado correctamente.");
});

client.on("auth_failure", (msg) => {
  estado = "desconectado";
  console.error("❌ Error de autenticación:", msg);
});

client.on("disconnected", (reason) => {
  estado = "desconectado";
  console.log("⚠️  WhatsApp desconectado:", reason);
  // Reintentar conexión después de 10 segundos
  setTimeout(() => {
    console.log("🔄 Reintentando conexión...");
    client.initialize();
  }, 10_000);
});

client.initialize();

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Normaliza el teléfono al formato de WhatsApp: 549XXXXXXXXXX@c.us
 * Acepta formatos argentinos: 11 2345-6789, 1123456789, +5491123456789, etc.
 */
function formatearTelefono(tel) {
  // Limpiar todo excepto dígitos y +
  let limpio = tel.replace(/[\s\-\(\)\.]+/g, "");
  let digitos = limpio.replace(/[^\d]/g, "");

  if (limpio.startsWith("+")) {
    // Ya tiene código de país → solo sacamos el +
    digitos = limpio.slice(1);
  } else if (digitos.startsWith("549")) {
    // OK
  } else if (digitos.startsWith("54")) {
    // OK
  } else {
    if (digitos.startsWith("0")) digitos = digitos.slice(1);
    if (digitos.startsWith("15")) digitos = digitos.slice(2);
    // Asumir Argentina
    if (!digitos.startsWith("549")) {
      digitos = "549" + digitos;
    }
  }

  return digitos + "@c.us";
}

// ── Rutas ─────────────────────────────────────────────────────────────────────

// Estado de la conexión
app.get("/estado", (req, res) => {
  res.json({ estado, timestamp: new Date().toISOString() });
});

// QR en texto plano (para terminales sin browser)
app.get("/qr", (req, res) => {
  if (estado !== "qr_pendiente" || !qrActual) {
    return res.status(400).json({ error: "No hay QR disponible actualmente.", estado });
  }
  res.json({ qr: qrActual, estado });
});

// Enviar mensaje
app.post("/enviar", async (req, res) => {
  const { telefono, mensaje } = req.body;

  if (!telefono || !mensaje) {
    return res.status(400).json({ error: "Faltan campos: telefono y/o mensaje." });
  }

  if (estado !== "conectado") {
    return res.status(503).json({
      error: `WhatsApp no está conectado. Estado actual: ${estado}`,
      estado,
    });
  }

  const chatId = formatearTelefono(telefono);

  try {
    await client.sendMessage(chatId, mensaje);
    console.log(`✓ Mensaje enviado a ${chatId}`);
    res.json({ ok: true, chatId });
  } catch (err) {
    console.error(`✗ Error enviando a ${chatId}:`, err.message);
    res.status(500).json({ error: err.message, chatId });
  }
});

// ── Arrancar ──────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n🚀 Servidor WhatsApp escuchando en http://localhost:${PORT}`);
  console.log(`   GET  /estado  → estado de la conexión`);
  console.log(`   GET  /qr      → QR para escanear`);
  console.log(`   POST /enviar  → { telefono, mensaje }\n`);
});
