const $ = id => document.getElementById(id);
const stage = $('stage'), frame = $('frame'), original = $('original'), edited = $('edited');
const status = $('status'), save = $('save'), split = $('split');
const worker = new Worker('./convert.js', {type: 'module'});
let job = 0, selection = 0, fileName = 'park-group', ready = false;
const recipe = () => document.querySelector('input[name="recipe"]:checked').value;

function fitFrame() {
  if (!original.width) return;
  const scale = Math.min((stage.clientWidth - 24) / original.width, (stage.clientHeight - 24) / original.height);
  frame.style.width = Math.round(scale * original.width) + 'px';
  frame.style.height = Math.round(scale * original.height) + 'px';
}
new ResizeObserver(fitFrame).observe(stage);
split.oninput = () => frame.style.setProperty('--cut', split.value + '%');

function convert() {
  if (!ready) return;
  const id = ++job;
  save.disabled = true;
  status.textContent = 'Detecting foreground and applying recipe…';
  try {
    const pixels = original.getContext('2d').getImageData(0, 0, original.width, original.height).data;
    worker.postMessage({id, pixels, width: original.width, height: original.height, selection, recipe: recipe()}, [pixels.buffer]);
  } catch {
    status.textContent = 'This image exceeds your browser’s memory limit. Try a smaller copy.';
  }
}

worker.onmessage = ({data}) => {
  if (data.id !== job) return;
  if (data.error) { status.textContent = data.error; return; }
  edited.getContext('2d').putImageData(new ImageData(data.pixels, edited.width, edited.height), 0, 0);
  save.disabled = false;
  split.disabled = false;
  status.textContent = '';
};
worker.onerror = () => { status.textContent = 'Conversion failed. Reload and try a smaller image.'; };

async function openImage(file, sample = false) {
  const id = ++selection;
  ++job;
  ready = false;
  save.disabled = split.disabled = true;
  status.textContent = 'Opening photo…';
  try {
    let bitmap;
    try { bitmap = await createImageBitmap(file); }
    catch (err) {
      if (!/\.hei[cf]$/i.test(file.name || '') && !/hei[cf]/i.test(file.type)) throw err;
      status.textContent = 'Decoding HEIC on this device…';
      const {heicTo} = await import('./vendor/heic-to.min.js');
      bitmap = await heicTo({blob: file, type: 'bitmap'});
    }
    if (id !== selection) { bitmap.close(); return; }
    fileName = sample ? 'park-group' : file.name.replace(/\.[^.]+$/, '');
    original.width = edited.width = bitmap.width;
    original.height = edited.height = bitmap.height;
    const ctx = original.getContext('2d', {willReadFrequently: true});
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, bitmap.width, bitmap.height);
    ctx.drawImage(bitmap, 0, 0);
    bitmap.close();
    edited.getContext('2d').drawImage(original, 0, 0);
    $('filename').textContent = sample ? 'Group portrait in the park' : file.name;
    $('dimensions').textContent = original.width + ' × ' + original.height;
    fitFrame();
    ready = true;
    convert();
  } catch {
    if (id === selection) status.textContent = 'Could not read that photo. Try a JPEG, PNG, WebP or HEIC file.';
  }
}

$('open').onclick = () => $('file').click();
$('file').onchange = event => {
  const file = event.target.files[0];
  if (file) openImage(file);
  event.target.value = '';
};
for (const control of document.querySelectorAll('input[name="recipe"]')) control.onchange = convert;
stage.ondragover = e => { e.preventDefault(); stage.classList.add('over'); };
stage.ondragleave = () => stage.classList.remove('over');
stage.ondrop = e => { e.preventDefault(); stage.classList.remove('over'); if (e.dataTransfer.files[0]) openImage(e.dataTransfer.files[0]); };
save.onclick = () => {
  const name = fileName + '-' + recipe() + '.jpg';
  edited.toBlob(blob => {
    if (!blob) { status.textContent = 'JPEG export failed. Please try a smaller image.'; return; }
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = name; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  }, 'image/jpeg', 0.95);
};
try {
  const response = await fetch('./park-group.jpg');
  if (!response.ok) throw new Error();
  const sample = await response.blob();
  if (!selection) await openImage(sample, true);
} catch { if (!selection) status.textContent = 'Choose a photo to begin.'; }
