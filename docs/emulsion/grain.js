// One seed per frame keeps the dye map, transmitted negative and print in register.
export function develop(pixels, quantiles) {
  let seed = 63;
  function sampleByte() {
    seed ^= seed << 13;
    seed ^= seed >>> 17;
    seed ^= seed << 5;
    return seed >>> 24;
  }
  for (let i = 0; i < pixels.length; i += 4) {
    for (let c = 0; c < 3; c++) {
      const row = pixels[i+c] * 256;
      let count = 0;
      for (let population = 0; population < 3; population++) {
        count += quantiles[population * 65536 + row + sampleByte()];
      }
      pixels[i+c] = Math.round(255 * count / 384);
    }
  }
}
