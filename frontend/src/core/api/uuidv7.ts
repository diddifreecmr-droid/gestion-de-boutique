/**
 * UUIDv7 (RFC 9562) : 48 bits d'horodatage en millisecondes, version 7, variante RFC, le reste
 * aléatoire. Le backend refuse tout autre format d'identifiant (`X-Device-Id` compris).
 */
const UUID_V7 = /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

export function isUuidV7(value: string): boolean {
  return UUID_V7.test(value);
}

export function uuidV7(now: number = Date.now(), random: Crypto = crypto): string {
  if (!Number.isSafeInteger(now) || now < 0 || now >= 2 ** 48) {
    throw new RangeError(`Horodatage UUIDv7 invalide : ${String(now)}`);
  }
  const bytes = random.getRandomValues(new Uint8Array(16));
  let time = now;
  for (let index = 5; index >= 0; index--) {
    bytes[index] = time % 256;
    time = Math.floor(time / 256);
  }
  bytes[6] = 0x70 | ((bytes[6] ?? 0) & 0x0f);
  bytes[8] = 0x80 | ((bytes[8] ?? 0) & 0x3f);
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
