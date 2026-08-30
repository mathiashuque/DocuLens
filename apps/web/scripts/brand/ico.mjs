/**
 * Packs PNG-encoded images into a multi-size ICO container (PNG-in-ICO is
 * valid since Windows Vista and universally supported by browsers).
 */
export function encodeIco(images) {
  const count = images.length;
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0); // reserved
  header.writeUInt16LE(1, 2); // type: icon
  header.writeUInt16LE(count, 4);

  const entries = [];
  const data = [];
  let offset = 6 + count * 16;

  for (const { size, png } of images) {
    const entry = Buffer.alloc(16);
    entry[0] = size >= 256 ? 0 : size; // width, 0 means 256
    entry[1] = size >= 256 ? 0 : size; // height
    entry[2] = 0; // color palette
    entry[3] = 0; // reserved
    entry.writeUInt16LE(1, 4); // color planes
    entry.writeUInt16LE(32, 6); // bits per pixel
    entry.writeUInt32LE(png.length, 8);
    entry.writeUInt32LE(offset, 12);
    entries.push(entry);
    data.push(png);
    offset += png.length;
  }

  return Buffer.concat([header, ...entries, ...data]);
}
