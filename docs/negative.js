// Expose a strip of the source. Only its 16-bit transmission values reach the reader.
function expose(pixels, start, negative, curves) {
  for (let i = 0, s = start; i < negative.length; i += 3, s += 4) {
    for (let c = 0; c < 3; c++) negative[i+c] = curves[c][pixels[s+c]];
  }
}

function readPrint(negative, reader, output, adapter) {
  const {density, weights: w} = reader;
  for (let i = 0, p = 0; i < negative.length; i += 3, p += 4) {
    const r = density[0][negative[i]], g = density[1][negative[i+1]], b = density[2][negative[i+2]];
    for (let c = 0; c < 3; c++) {
      const value = (w[0][c] + r*w[1][c] + g*w[2][c] + b*w[3][c]
        + r*r*w[4][c] + g*g*w[5][c] + b*b*w[6][c] + r*g*w[7][c] + g*b*w[8][c] + b*r*w[9][c]);
      const print = Math.max(0, Math.min(1, value));
      output[p+c] = 255 * (adapter ? (print - 0.5) * (1 + adapter[c+3]) + 0.5 + adapter[c] : print);
    }
    output[p+3] = 255;
  }
}

let loading;
async function loadModel() {
  const response = await fetch('./negative-model.json');
  if (!response.ok) throw new Error('Could not load the negative model. Please retry.');
  const model = await response.json();
  model.density = model.lo.map((lo, c) => Float32Array.from({length: 65536}, (_, v) =>
    Math.max(-0.5, Math.min(1.5, (-Math.log10(Math.max(v,1)/65535)-lo)/(model.hi[c]-lo)))));
  return model;
}

export async function negativePipeline(pixels, calibrated, preview, branch) {
  loading ??= loadModel().catch(error => { loading = undefined; throw error; });
  const model = await loading;
  const writer = (branch === 'A' || branch === 'C') ? model.writer : (calibrated ? model.balanced : model.raw);
  const readerAdapter = (branch === 'B' || branch === 'C') ? model.readerAdapter : null;
  const block = 16384;
  const buffer = new Uint16Array(block*3);
  const output = new Uint8ClampedArray(block*4);
  for (let start = 0; start < pixels.length; start += block*4) {
    const count = Math.min(block, (pixels.length-start)/4);
    const negative = buffer.subarray(0,count*3);
    expose(pixels, start, negative, writer);
    if (preview) {
      for (let i=0; i<count; i++) {
        for (let c=0; c<3; c++) {
          const t=negative[i*3+c]/65535;
          output[i*4+c]=255*(t<=0.0031308 ? 12.92*t : 1.055*t**(1/2.4)-0.055);
        }
        output[i*4+3]=255;
      }
    } else {
      readPrint(negative, model, output, readerAdapter);
    }
    pixels.set(output.subarray(0,count*4), start);
  }
}
