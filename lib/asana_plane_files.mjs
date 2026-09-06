import fs from 'node:fs';
import path from 'node:path';
import dns from 'node:dns/promises';
import https from 'node:https';
import net from 'node:net';
import crypto from 'node:crypto';
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';

export function isPublicAddress(address) {
  if (net.isIP(address) === 4) {
    const [a,b,c] = address.split('.').map(Number);
    return !(a === 0 || a === 10 || a === 127 || a >= 224 || (a === 100 && b >= 64 && b <= 127) ||
      (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) ||
      (a === 192 && (b === 0 || b === 168)) || (a === 198 && (b === 18 || b === 19 || (b === 51 && c === 100))) ||
      (a === 203 && b === 0 && c === 113));
  }
  if (net.isIP(address) === 6) {
    const normalized = new URL(`https://[${address}]/`).hostname.slice(1,-1).toLowerCase();
    const [first, second] = normalized.split(':');
    const a = Number.parseInt(first, 16); const b = Number.parseInt(second || '0', 16);
    // Permit global-unicast 2000::/3, excluding the entire special-use
    // 2001::/23 (including compressed Teredo), documentation and 6to4.
    return (a & 0xe000) === 0x2000 && !(a === 0x2001 && (b < 0x200 || b === 0xdb8)) && a !== 0x2002 && a !== 0x3fff;
  }
  return false;
}

export async function publicTarget(value, lookup = dns.lookup) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password || (url.port && url.port !== '443')) throw new Error('Unsafe attachment URL');
  const hostname = url.hostname.replace(/^\[|\]$/g, '');
  if (hostname.toLowerCase() === 'localhost' || hostname.toLowerCase().endsWith('.localhost')) throw new Error('Private attachment hostname');
  const records = net.isIP(hostname) ? [{ address: hostname, family: net.isIP(hostname) }] : await lookup(hostname, { all: true, verbatim: true });
  if (!records.length || records.some(record => !isPublicAddress(record.address))) throw new Error('Private or reserved attachment address');
  return { url, records };
}

export async function downloadAttachment(value, file, { maxBytes = 110 * 1024 * 1024 } = {}) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  let next = value;
  for (let redirect = 0; redirect <= 5; redirect++) {
    const { url, records } = await publicTarget(next);
    const response = await new Promise((resolve, reject) => {
      const request = https.get(url, {
        agent: false, headers: { 'User-Agent': 'MEGAI-private-migration/1.0' },
        lookup(_host, options, callback) {
          if (options?.all) callback(null, records);
          else callback(null, records[0].address, records[0].family);
        },
      }, resolve);
      request.setTimeout(120000, () => request.destroy(new Error('Attachment timeout')));
      request.on('error', () => reject(new Error('Attachment transport failed')));
    });
    if ([301,302,303,307,308].includes(response.statusCode)) {
      const location = response.headers.location; response.resume();
      if (!location || redirect === 5) throw new Error('Attachment redirect limit');
      next = new URL(location, url).href; continue;
    }
    if (response.statusCode !== 200) { response.resume(); throw new Error(`Attachment HTTP ${response.statusCode}`); }
    const expected = response.headers['content-length'] === undefined ? null : Number(response.headers['content-length']);
    if (expected !== null && (!Number.isSafeInteger(expected) || expected < 0 || expected > maxBytes)) { response.destroy(); throw new Error('Attachment size rejected'); }
    const tmp = file + '.' + crypto.randomUUID() + '.tmp';
    const digest = crypto.createHash('sha256'); let bytes = 0;
    const meter = new Transform({ transform(chunk, _encoding, callback) {
      bytes += chunk.length;
      if (bytes > maxBytes) callback(new Error('Attachment exceeds byte limit'));
      else { digest.update(chunk); callback(null, chunk); }
    } });
    try {
      await pipeline(response, meter, fs.createWriteStream(tmp, { flags: 'wx', mode: 0o600 }));
      if (expected !== null && bytes !== expected) throw new Error('Attachment length mismatch');
      if (fs.existsSync(file) && fs.lstatSync(file).isSymbolicLink()) throw new Error('Symlink attachment destination');
      const fileFd = fs.openSync(tmp, 'r');
      try { fs.fsyncSync(fileFd); } finally { fs.closeSync(fileFd); }
      fs.renameSync(tmp, file);
      const directoryFd = fs.openSync(path.dirname(file), 'r');
      try { fs.fsyncSync(directoryFd); } finally { fs.closeSync(directoryFd); }
      return { bytes, sha256: digest.digest('hex'), content_type: response.headers['content-type'] ?? null };
    } catch (error) { try { fs.unlinkSync(tmp); } catch {} throw error; }
  }
  throw new Error('Attachment redirect limit');
}
