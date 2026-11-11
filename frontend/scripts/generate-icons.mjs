/**
 * Génère les icônes PWA PROVISOIRES (carré primaire + pavé clair) à partir des tokens.
 * À remplacer par le vrai logo. Usage : `npm run icons` (fichiers versionnés dans public/icons).
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { deflateSync } from "node:zlib";
import { readTokenFromFile } from "../config/tokens.ts";

const OUT = new URL("../public/icons/", import.meta.url);

function hexToRgb(hex) {
  const match = /^#([0-9a-f]{6})$/i.exec(hex);
  if (match === null) throw new Error(`Couleur hexadécimale attendue, reçu « ${hex} »`);
  const n = Number.parseInt(match[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(buf) {
  let c = 0xffffffff;
  for (const byte of buf) c = CRC_TABLE[(c ^ byte) & 255] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type, "ascii"), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body));
  return Buffer.concat([length, body, crc]);
}

/** PNG RVB : fond `bg`, pavé central `fg` (60 % du côté, zone sûre « maskable »). */
function png(size, bg, fg) {
  const inner = Math.round(size * 0.3);
  const rows = [];
  for (let y = 0; y < size; y++) {
    const row = Buffer.alloc(1 + size * 3);
    for (let x = 0; x < size; x++) {
      const inside = x >= inner && x < size - inner && y >= inner && y < size - inner;
      const [r, g, b] = inside ? fg : bg;
      row.set([r, g, b], 1 + x * 3);
    }
    rows.push(row);
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(size, 0);
  header.writeUInt32BE(size, 4);
  header.set([8, 2, 0, 0, 0], 8); // 8 bits, RVB, sans entrelacement
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", header),
    chunk("IDAT", deflateSync(Buffer.concat(rows))),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

const primary = readTokenFromFile("--color-primary");
const onPrimary = readTokenFromFile("--color-on-primary");
mkdirSync(OUT, { recursive: true });
for (const size of [192, 512]) {
  writeFileSync(
    new URL(`icon-${size}.png`, OUT),
    png(size, hexToRgb(primary), hexToRgb(onPrimary)),
  );
}
writeFileSync(
  new URL("icon.svg", OUT),
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><title>Icône provisoire</title>` +
    `<rect width="100" height="100" fill="${primary}"/>` +
    `<rect x="30" y="30" width="40" height="40" fill="${onPrimary}"/></svg>\n`,
);
console.log(`Icônes provisoires générées (${primary} / ${onPrimary}) dans public/icons/`);
