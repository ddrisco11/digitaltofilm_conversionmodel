import * as ort from './vendor/foreground/ort.wasm.min.mjs';

const size = 320;
ort.env.wasm.numThreads = 1;
ort.env.wasm.wasmPaths = new URL('./vendor/foreground/', import.meta.url).href;
let session;

export function thumbnail(pixels, width, height, edge) {
  const source = new OffscreenCanvas(width, height);
  source.getContext('2d').putImageData(new ImageData(pixels, width, height), 0, 0);
  const small = new OffscreenCanvas(edge, edge);
  const ctx = small.getContext('2d');
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(source, 0, 0, edge, edge);
  source.width = source.height = 1;
  return ctx.getImageData(0, 0, edge, edge).data;
}

export async function foregroundMask(rgba) {
  session ??= ort.InferenceSession.create(new URL('./vendor/foreground/u2netp.onnx', import.meta.url).href,
    {executionProviders: ['wasm']}).catch(error => { session = undefined; throw error; });
  const engine = await session;
  const plane = size * size;
  const rgb = new Float32Array(3 * plane);
  const means = [0.485, 0.456, 0.406], stds = [0.229, 0.224, 0.225];
  let peak = 1;
  for (let i = 0; i < rgba.length; i += 4) peak = Math.max(peak, rgba[i], rgba[i+1], rgba[i+2]);
  for (let c = 0; c < 3; c++)
    for (let i = 0; i < plane; i++)
      rgb[c*plane+i] = (rgba[4*i+c] / peak - means[c]) / stds[c];
  const name = engine.outputNames[0];
  const outputs = await engine.run({[engine.inputNames[0]]: new ort.Tensor('float32', rgb, [1,3,size,size])}, [name]);
  const mask = Uint8ClampedArray.from(outputs[name].data, v => v * 255);
  outputs[name].dispose();
  return mask;
}

// Expand one row at a time to keep the native-resolution working set small.
export function maskSampler(mask, width, height) {
  const left = new Int32Array(width), blend = new Float32Array(width), row = new Float32Array(width);
  for (let x = 0; x < width; x++) {
    const u = Math.max(0, Math.min(size-1, (x+0.5)*size/width-0.5));
    left[x] = Math.floor(u); blend[x] = u-left[x];
  }
  return y => {
    const v = Math.max(0, Math.min(size-1, (y+0.5)*size/height-0.5));
    const top = Math.floor(v), bottom = Math.min(size-1, top+1), t = v-top;
    for (let x=0; x<width; x++) {
      const l=left[x], r=Math.min(size-1,l+1), f=blend[x];
      const a=mask[top*size+l]*(1-f)+mask[top*size+r]*f;
      const b=mask[bottom*size+l]*(1-f)+mask[bottom*size+r]*f;
      row[x]=(a+(b-a)*t)/255;
    }
    return row;
  };
}
