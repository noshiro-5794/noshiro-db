/**
 * Rebuilds every platform icon from the character artwork.
 *
 *   pnpm icons
 *
 * `public/assets/brand/mark.png` is the authored master: the illustration,
 * trimmed to its own bounds so nothing is ever cropped. Everything below is
 * composed from that single file and the geometry constants in this script, so
 * the browser tab, the installed app and the social card can never disagree
 * about framing again.
 *
 * Two framings come out of it:
 *
 *   tile  - the character on transparency, filling the canvas. This is the
 *           artwork as drawn: the browser tab, the launcher and the in-app logo
 *           all show it the way it was originally used.
 *   bleed - the character on an opaque plate, scaled into the maskable safe
 *           zone, for the two platforms that cannot show transparency: Apple
 *           touch icons and Android maskable icons crop the canvas with their
 *           own mask, so they need a filled square.
 *
 * The artwork is a bitmap, so there is deliberately no SVG in this set: an SVG
 * wrapper would only embed the same pixels and look no sharper. `icon-512.png`
 * doubles as the in-app logo, where it is displayed at 24-48 CSS pixels.
 *
 * `favicon.ico` is written as an uncompressed 16/32/48 bitmap set, because some
 * launchers still ignore PNG-compressed entries.
 */
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { chromium } from '@playwright/test';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const publicDirectory = path.join(repositoryRoot, 'public');
const markPath = path.join(publicDirectory, 'assets', 'brand', 'mark.png');
const markBase64 = (await readFile(markPath)).toString('base64');
const markDataUrl = `data:image/png;base64,${markBase64}`;

/** Geometry shared by the CSS compositions and the ICO bitmap. */
const geometry = {
  /** Margin around the character on the transparent framing. */
  tileInset: 0,
  /** Corner radius of the plate, as a share of the canvas. */
  cornerRadius: 0.226,
  /**
   * Character width on a full-bleed icon. The artwork is widest across the
   * middle, so 72% keeps every stroke inside the maskable safe circle.
   */
  bleedInset: 0.14,
  plate: { color: '#ffffff', hairline: 'rgba(20, 20, 26, 0.06)' },
};

const canvas = 512;
const icoSizes = [16, 32, 48];

const pngTargets = [
  { file: 'favicon-16x16.png', framing: 'tile', size: 16 },
  { file: 'favicon-32x32.png', framing: 'tile', size: 32 },
  { file: 'apple-touch-icon.png', framing: 'bleed', size: 180 },
  { file: 'icon-192.png', framing: 'tile', size: 192 },
  { file: 'icon-512.png', framing: 'tile', size: 512 },
  { file: 'icon-maskable-192.png', framing: 'bleed', size: 192 },
  { file: 'icon-maskable-512.png', framing: 'bleed', size: 512 },
];

const ogImage = { height: 630, width: 1200 };

const fontStack =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Hiragino Sans", "Microsoft YaHei", sans-serif';

/** The transparent framing shows the artwork exactly as authored. */
function iconMarkup(size, framing) {
  const inset = framing === 'bleed' ? geometry.bleedInset : geometry.tileInset;
  const background =
    framing === 'bleed'
      ? `background: ${geometry.plate.color}; box-shadow: inset 0 0 0 1px ${geometry.plate.hairline};`
      : '';
  return `<span style="
    width: ${String(size)}px;
    height: ${String(size)}px;
    position: relative;
    overflow: hidden;
    ${background}
  ">
    <img alt="" src="${markDataUrl}" style="position:absolute; inset:${String(inset * 100)}%; width:${String(
      (1 - inset * 2) * 100,
    )}%; height:${String((1 - inset * 2) * 100)}%; object-fit:contain;" />
  </span>`;
}

function iconDocument(size, framing) {
  return `<!doctype html>
<html><head><meta charset="utf-8"><style>
  html, body { margin: 0; background: transparent; }
  body > span { display: block; }
</style></head>
<body>${iconMarkup(size, framing)}</body></html>`;
}

function ogDocument({ height, width }) {
  const title = '动画与 Galgame 的开放资料库';
  const body = '搜索日语、中文或英文标题，都能落到同一部作品；当季放送时间、简介与制作阵容，随时可查。';
  return `<!doctype html>
<html><head><meta charset="utf-8"><style>
  * { box-sizing: border-box; }
  html, body { margin: 0; }
  body {
    background: #111113;
    color: #f1f1f3;
    font-family: ${fontStack};
    height: ${String(height)}px;
    overflow: hidden;
    position: relative;
    width: ${String(width)}px;
  }
  .glow {
    background: radial-gradient(52% 46% at 50% 0%, rgba(139, 124, 182, 0.42) 0%, rgba(139, 124, 182, 0) 72%);
    inset: 0;
    position: absolute;
  }
  .frame {
    display: flex;
    flex-direction: column;
    height: 100%;
    justify-content: space-between;
    padding: 72px 80px 64px;
    position: relative;
  }
  .brand { align-items: center; display: flex; gap: 18px; }
  .brand > span { border-radius: 22% !important; }
  .brand strong { font-size: 28px; font-weight: 600; letter-spacing: -0.01em; }
  h1 { font-size: 60px; font-weight: 600; letter-spacing: -0.02em; line-height: 1.18; margin: 64px 0 0; max-width: 900px; }
  p { color: #a4a4ad; font-size: 24px; line-height: 1.6; margin: 24px 0 0; max-width: 820px; }
  footer { align-items: baseline; color: #898993; display: flex; font-size: 20px; justify-content: space-between; }
</style></head>
<body>
  <div class="glow"></div>
  <div class="frame">
    <div>
      <div class="brand">${iconMarkup(64, 'bleed')}<strong>Noshiro DB</strong></div>
      <h1>${title}</h1>
      <p>${body}</p>
    </div>
    <footer><span>Bangumi · AniList · MyAnimeList</span><span>app.noshiro.moe</span></footer>
  </div>
</body></html>`;
}

/**
 * Renders the icon at the given size and returns raw RGBA pixels, so the
 * multi-size ICO matches the PNG icons exactly.
 */
async function readTilePixels(page, size) {
  return page.evaluate(
    async ({ constants, source, targetSize }) => {
      const image = new Image();
      image.src = source;
      await image.decode();

      const surface = document.createElement('canvas');
      surface.width = targetSize;
      surface.height = targetSize;
      const context = surface.getContext('2d');
      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = 'high';

      const inset = constants.tileInset * targetSize;
      context.drawImage(image, inset, inset, targetSize - inset * 2, targetSize - inset * 2);
      return Array.from(context.getImageData(0, 0, targetSize, targetSize).data);
    },
    {
      constants: {
        tileInset: geometry.tileInset,
      },
      source: markDataUrl,
      targetSize: size,
    },
  );
}

function bitmapInfoHeader(size) {
  const header = Buffer.alloc(40);
  header.writeUInt32LE(40, 0);
  header.writeInt32LE(size, 4);
  header.writeInt32LE(size * 2, 8);
  header.writeUInt16LE(1, 12);
  header.writeUInt16LE(32, 14);
  return header;
}

function bitmapPixels(rgba, size) {
  const pixels = Buffer.alloc(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const source = ((size - 1 - y) * size + x) * 4;
      const target = (y * size + x) * 4;
      pixels[target] = rgba[source + 2];
      pixels[target + 1] = rgba[source + 1];
      pixels[target + 2] = rgba[source];
      pixels[target + 3] = rgba[source + 3];
    }
  }
  return pixels;
}

/** 1bpp transparency mask, one row per line and padded to four bytes. */
function transparencyMask(size) {
  return Buffer.alloc(Math.ceil(size / 32) * 4 * size);
}

function buildIco(images) {
  const directory = Buffer.alloc(6 + images.length * 16);
  directory.writeUInt16LE(0, 0);
  directory.writeUInt16LE(1, 2);
  directory.writeUInt16LE(images.length, 4);

  let offset = directory.length;
  const payloads = [];
  images.forEach((image, index) => {
    const entry = 6 + index * 16;
    directory.writeUInt8(image.size >= 256 ? 0 : image.size, entry);
    directory.writeUInt8(image.size >= 256 ? 0 : image.size, entry + 1);
    directory.writeUInt16LE(1, entry + 4);
    directory.writeUInt16LE(32, entry + 6);
    directory.writeUInt32LE(image.data.length, entry + 8);
    directory.writeUInt32LE(offset, entry + 12);
    payloads.push(image.data);
    offset += image.data.length;
  });

  return Buffer.concat([directory, ...payloads]);
}

const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 1 });

for (const target of pngTargets) {
  await page.setViewportSize({ height: target.size, width: target.size });
  await page.setContent(iconDocument(target.size, target.framing));
  await page.screenshot({
    omitBackground: target.framing === 'tile',
    path: path.join(publicDirectory, target.file),
  });
  console.log(`rendered ${target.file} (${String(target.size)}px, ${target.framing})`);
}

await page.setViewportSize({ height: ogImage.height, width: ogImage.width });
await page.setContent(ogDocument(ogImage));
await page.screenshot({ path: path.join(publicDirectory, 'og-image.png') });
console.log(`rendered og-image.png (${String(ogImage.width)}x${String(ogImage.height)})`);

const icoImages = [];
for (const size of icoSizes) {
  const rgba = await readTilePixels(page, size);
  icoImages.push({
    data: Buffer.concat([bitmapInfoHeader(size), bitmapPixels(rgba, size), transparencyMask(size)]),
    size,
  });
}
await writeFile(path.join(publicDirectory, 'favicon.ico'), buildIco(icoImages));
console.log(`rendered favicon.ico (${icoSizes.join('/')})`);

await browser.close();
