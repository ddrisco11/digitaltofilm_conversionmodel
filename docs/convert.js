import {foregroundMask, maskSampler, thumbnail} from './foreground.js';

// Same 33³ red-fastest table layout as the Python/Pillow converter.
const clip = (v, min, max) => Math.min(max, Math.max(min, v));

async function load(url, binary = false) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('Could not load the color model. Please reload.');
  return binary ? new Float32Array(await response.arrayBuffer()) : response.json();
}

let weights;
function buildTable(model, data, context) {
  const count = 3 * model.size ** 3;
  if (data.length !== count * 4) throw new Error('Incomplete color model.');
  const coefficients = context.map((v, i) => clip((v - model.mean[i]) / model.scale[i], -3, 3));
  const table = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    let value = data[i];
    for (let j = 0; j < 3; j++) value += data[(j + 1) * count + i] * coefficients[j];
    table[i] = 255 * clip(value, 0, 1);
  }
  return table;
}

function toneCurve([xs, ys]) {
  return Uint8ClampedArray.from({length: 256}, (_, v) => {
    const k = xs.findIndex(x => x >= v);
    if (k <= 0) return ys[0];
    const t = (v - xs[k - 1]) / (xs[k] - xs[k - 1]);
    return ys[k - 1] + t * (ys[k] - ys[k - 1]);
  });
}

function descriptor(data) {
  let mean = 0, squares = 0, cast = 0;
  for (let i = 0; i < data.length; i += 4) {
    const luma = (0.2126*data[i] + 0.7152*data[i+1] + 0.0722*data[i+2]) / 255;
    mean += luma;
    squares += luma*luma;
    cast += (data[i]-data[i+2])/255;
  }
  const n = data.length / 4;
  mean /= n;
  return [mean, Math.sqrt(Math.max(0, squares/n - mean*mean)), cast/n];
}

function apply(pixels, size, table, curves, width, maskRow) {
  const low = new Uint16Array(256);
  const frac = new Float32Array(256);
  for (let v = 0; v < 256; v++) {
    const position = v * (size - 1) / 255;
    low[v] = Math.min(size - 2, Math.floor(position));
    frac[v] = position - low[v];
  }
  const green = 3 * size, blue = green * size;
  let row;
  for (let i = 0; i < pixels.length; i += 4) {
    const xPixel = (i / 4) % width;
    if (maskRow && !xPixel) row = maskRow(i / 4 / width);
    const foreground = row ? row[xPixel] : 0;
    if (foreground === 1) continue;
    const r = pixels[i], g = pixels[i + 1], b = pixels[i + 2];
    const base = 3 * low[r] + green * low[g] + blue * low[b];
    const x = frac[r], y = frac[g], z = frac[b];
    for (let c = 0; c < 3; c++) {
      const n = base + c;
      const near = (1-y)*((1-x)*table[n]+x*table[n+3]) + y*((1-x)*table[n+green]+x*table[n+green+3]);
      const far = (1-y)*((1-x)*table[n+blue]+x*table[n+blue+3]) + y*((1-x)*table[n+blue+green]+x*table[n+blue+green+3]);
      const value = Math.round((1-z)*near + z*far);
      const graded = curves ? curves[c][value] : value;
      pixels[i+c] += (graded - pixels[i+c]) * (1 - foreground);
    }
  }
}

const spectralTables = new Map();

async function spectralTable(stage) {
  if (!['exposure', 'grains', 'negative', 'print'].includes(stage)) throw new Error('Unknown spectral stage.');
  if (!spectralTables.has(stage)) {
    const response = await fetch('./emulsion/' + stage + '.bin');
    if (!response.ok) throw new Error('Could not load this spectral stage. Please retry.');
    const table = new Uint8Array(await response.arrayBuffer());
    if (table.length !== (stage === 'grains' ? 3 * 65536 : 65 ** 3 * 3)) throw new Error('Incomplete spectral table. Please reload.');
    spectralTables.set(stage, table);
  }
  return spectralTables.get(stage);
}

let cachedSelection, cachedMask;
async function convert({id, pixels, width, height, selection, recipe, pipeline, calibrated, preview, branch, physicalStage}) {
  try {
    if (pipeline === 'physics') {
      apply(pixels, 65, await spectralTable('exposure'), null, width);
      if (physicalStage !== 'exposure') {
        const {develop} = await import('./emulsion/grain.js');
        develop(pixels, await spectralTable('grains'));
        if (physicalStage !== 'dyes') apply(pixels, 65, await spectralTable(physicalStage), null, width);
      }
      self.postMessage({id, pixels}, [pixels.buffer]);
      return;
    }
    if (pipeline === 'negative') {
      const {negativePipeline} = await import('./negative.js');
      // Keep the intermediate visible while the full-size canvas shows the print.
      const scale = Math.min(1, 420 / Math.max(width, height));
      const thumbWidth = Math.max(1, Math.round(width*scale));
      const thumbHeight = Math.max(1, Math.round(height*scale));
      const thumb = new Uint8ClampedArray(thumbWidth * thumbHeight * 4);
      for (let y=0; y<thumbHeight; y++) {
        for (let x=0; x<thumbWidth; x++) {
          const i=4*(Math.floor(y*height/thumbHeight)*width+Math.floor(x*width/thumbWidth));
          thumb.set(pixels.subarray(i,i+4),4*(y*thumbWidth+x));
        }
      }
      await negativePipeline(thumb, calibrated, true, branch);
      await negativePipeline(pixels, calibrated, preview, branch);
      self.postMessage({id, pixels, thumb, thumbWidth, thumbHeight}, [pixels.buffer, thumb.buffer]);
      return;
    }
    weights ??= Promise.all([load('./model.json'), load('./lut.bin', true)]);
    const [model, data] = await weights;
    const curves = recipe === 'gold' ? model.curves.map(toneCurve) : null;
    if (selection !== cachedSelection) {
      cachedMask = await foregroundMask(thumbnail(pixels, width, height, 320));
      cachedSelection = selection;
    }
    const first = descriptor(thumbnail(pixels, width, height, 64));
    apply(pixels, model.size, buildTable(model, data, first), curves, width);
    const second = descriptor(thumbnail(pixels, width, height, 64));
    apply(pixels, model.size, buildTable(model, data, second), curves, width,
      maskSampler(cachedMask, width, height));
    self.postMessage({id, pixels}, [pixels.buffer]);
  } catch (error) {
    weights = undefined;
    self.postMessage({id, error: error.message});
  }
}
let queue = Promise.resolve();
self.onmessage = ({data}) => { queue = queue.then(() => convert(data)); };
