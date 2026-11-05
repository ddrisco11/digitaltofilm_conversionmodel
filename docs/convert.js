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

function apply(pixels, size, table, curves) {
  const low = new Uint16Array(256);
  const frac = new Float32Array(256);
  for (let v = 0; v < 256; v++) {
    const position = v * (size - 1) / 255;
    low[v] = Math.min(size - 2, Math.floor(position));
    frac[v] = position - low[v];
  }
  const green = 3 * size, blue = green * size;
  for (let i = 0; i < pixels.length; i += 4) {
    const r = pixels[i], g = pixels[i + 1], b = pixels[i + 2];
    const base = 3 * low[r] + green * low[g] + blue * low[b];
    const x = frac[r], y = frac[g], z = frac[b];
    for (let c = 0; c < 3; c++) {
      const n = base + c;
      const near = (1-y)*((1-x)*table[n]+x*table[n+3]) + y*((1-x)*table[n+green]+x*table[n+green+3]);
      const far = (1-y)*((1-x)*table[n+blue]+x*table[n+blue+3]) + y*((1-x)*table[n+blue+green]+x*table[n+blue+green+3]);
      const value = Math.round((1-z)*near + z*far);
      pixels[i+c] = curves ? curves[c][value] : value;
    }
  }
}

self.onmessage = async ({data: {id, pixels, context, recipe}}) => {
  try {
    weights ??= Promise.all([load('./model.json'), load('./lut.bin', true)]);
    const [model, data] = await weights;
    const curves = recipe === 'gold' ? model.curves.map(toneCurve) : null;
    apply(pixels, model.size, buildTable(model, data, context), curves);
    self.postMessage({id, pixels}, [pixels.buffer]);
  } catch (error) {
    weights = undefined;
    self.postMessage({id, error: error.message});
  }
};
