const $=id=>document.getElementById(id);
let source,worker,name='park-group',probe=[.5,.5],history=[],runHistory=[],lastSeries='',busy=false;
const canvases=['input','output','negative'];
const formulas={
 exposure:'Hⱼ ∝ Σ L(λ) ηⱼ(λ) λ Δλ\nP(active) = P[Poisson(H × sensitivity) ≥ 4]',
 film:'∂C/∂t = D∇²C + b(1−C) − reaction\nΔAg = (A−Ag)[1−exp(−kCΔt)]\nOxidized developer + coupler → dye',
 'paper-exposure':'T(λ) = 10^[−0.10 − 2Σdⱼaⱼ(λ)]\nHpaper = 0.35 Σ T(λ) lamp(λ) captureⱼ(λ)',
 paper:'A new grain population activates on paper.\nDeveloper diffuses and is consumed.\nOxidized developer + coupler → paper dye',
 reflection:'R = r + t²Rg/(1−rRg)\nXYZ ∝ Σ D50(λ) R(λ) CMF(λ) Δλ'
};
function plot(id,series){
 const c=$(id),ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);
 ctx.fillStyle='#66705f';ctx.font='12px sans-serif';ctx.fillText('1',8,17);ctx.fillText('0',8,158);ctx.strokeStyle='#c7cebd';ctx.beginPath();ctx.moveTo(30,12);ctx.lineTo(30,155);ctx.lineTo(585,155);ctx.stroke();
 for(const {values,color} of series){
  ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.beginPath();
  values.forEach((v,i)=>{const x=30+i*550/Math.max(1,values.length-1),y=155-Math.max(0,Math.min(1,v))*140;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();
 }
}
function controls(running){
 busy=running; $('run').disabled=running||!source;$('choose').disabled=running;
 $('resolution').disabled=running;$('cancel').disabled=!running;
}
function prepare(){
 if(!source)return;
 const size=Number($('resolution').value),scale=size?Math.min(1,size/Math.max(source.width,source.height)):1;
 const w=Math.max(1,Math.round(source.width*scale)),h=Math.max(1,Math.round(source.height*scale));
 for(const id of canvases){$(id).width=w;$(id).height=h;}
 $('input').getContext('2d').drawImage(source,0,0,w,h);
 $('input-caption').textContent=name+' · '+w+' × '+h;
 $('output-caption').textContent='Print · '+w+' × '+h;
 $('save').disabled=true;$('trace').disabled=true;
 $('probe-label').textContent='Pixel '+Math.floor(probe[0]*w)+', '+Math.floor(probe[1]*h);
 $('phase').textContent='At the measurement point';
 $('progress').value=0;
 for(const field of ['developer','dye','oxidized','coupler'])$(field).textContent='—';
 plot('chart',[]);plot('spectrum',[]);
 $('status').textContent='Ready. Select a measurement point or develop the photo.';
}
async function open(blob,label){
 controls(true);
 try{
  let decoded=blob;
  if(/\.hei[cf]$/i.test(label)||/hei[cf]/i.test(blob.type)){
   const {heicTo}=await import('../vendor/heic-to.min.js');
   decoded=await heicTo({blob,type:'image/png'});
  }
  const next=await createImageBitmap(decoded,{imageOrientation:'from-image'});
  if(next.width*next.height>32_000_000){next.close();throw new Error('Please choose an image up to 32 megapixels.');}
  source?.close();source=next;probe=[.5,.5];name=label.replace(/\.[^.]+$/,'');prepare();
 }catch(error){$('status').textContent=error.message;}
 finally{controls(false);}
}
$('choose').onclick=()=>$('file').click();
$('file').onchange=()=>{if($('file').files[0])open($('file').files[0],$('file').files[0].name);};
$('resolution').onchange=prepare;
$('input').onclick=e=>{
 if(busy)return;
 const rect=$('input').getBoundingClientRect(),c=$('input');
 const scale=Math.min(rect.width/c.width,rect.height/c.height);
 const x=(e.clientX-rect.left-(rect.width-c.width*scale)/2)/(c.width*scale);
 const y=(e.clientY-rect.top-(rect.height-c.height*scale)/2)/(c.height*scale);
 if(x<0||x>=1||y<0||y>=1)return;
 probe=[x,y];$('probe-label').textContent='Pixel '+Math.floor(x*c.width)+', '+Math.floor(y*c.height);
};
$('run').onclick=()=>{
 controls(true);$('save').disabled=true;$('trace').disabled=true;
 history=[];runHistory=[];lastSeries='';$('progress').value=0;
 plot('chart',[]);plot('spectrum',[]);
 for(const key of ['developer','dye','oxidized','coupler'])$(key).textContent='—';
 const w=$('input').width,h=$('input').height,started=performance.now();
 const seed=crypto.getRandomValues(new Uint32Array(1))[0];
 const pixels=$('input').getContext('2d').getImageData(0,0,w,h).data;
 worker?.terminate();worker=new Worker('./chemistry/worker.js',{type:'module'});
 worker.onerror=()=>{$('status').textContent='The worker stopped. Try a smaller render size.';controls(false);};
 worker.onmessage=({data})=>{
  if(data.type==='error'){$('status').textContent=data.message;controls(false);return;}
  if(data.type==='complete'){
   $('output').getContext('2d').putImageData(new ImageData(data.pixels,w,h),0,0);
   $('progress').value=1;$('status').textContent='Complete · '+((performance.now()-started)/1000).toFixed(1)+' seconds';
   $('save').disabled=false;$('trace').disabled=false;controls(false);return;
  }
  if(data.phase==='negative-image'){$('negative').getContext('2d').putImageData(new ImageData(data.pixels,w,h),0,0);return;}
  if(data.phase==='spectrum'){plot('spectrum',[{values:data.spectrum,color:'#517a54'}]);runHistory.push(data);return;}
  runHistory.push({...data,width:w,height:h,seed,probe});
  if(formulas[data.phase]){
   $('equation').textContent=formulas[data.phase];
   document.querySelectorAll('[data-phase]').forEach(el=>el.classList.toggle('active',el.dataset.phase===data.phase));
  }
  if(data.step){
   const key=data.phase+'-'+data.channel;
   if(key!==lastSeries){history=[];lastSeries=key;}
   history.push(data);
   $('phase').textContent=(data.phase==='film'?'Film':'Paper')+' · '+['cyan','magenta','yellow'][data.channel];
   $('time').textContent=data.time.toFixed(1)+' relative time units · step '+data.step+' / '+data.steps;
   for(const field of ['developer','dye','oxidized','coupler'])$(field).textContent=data[field].toFixed(4);
   plot('chart',[{values:history.map(v=>v.developer),color:'#4873a3'},{values:history.map(v=>v.dye),color:'#9c5a23'}]);
   $('progress').value=(data.phase==='film'?.12:.55)+(data.channel+data.step/data.steps)/3*.3;
   $('status').textContent='Developing '+data.phase+' · '+['cyan','magenta','yellow'][data.channel];
  }else if(data.fraction!==undefined){
   const start={exposure:0,'paper-exposure':.42,reflection:.85}[data.phase];
   $('progress').value=start+data.fraction*(data.phase==='reflection'?.15:.12);
   $('status').textContent={exposure:'Exposing film','paper-exposure':'Exposing paper',reflection:'Computing spectral reflection'}[data.phase]+' · '+Math.round(data.fraction*100)+'%';
  }
 };
 worker.postMessage({pixels,width:w,height:h,seed,probe:Math.min(w*h-1,Math.floor(probe[1]*h)*w+Math.floor(probe[0]*w))},[pixels.buffer]);
};
$('cancel').onclick=()=>{worker?.terminate();controls(false);$('status').textContent='Cancelled. Ready for another run.';};
function download(blob,filename){const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
$('save').onclick=()=>$('output').toBlob(blob=>download(blob,name+'-chemistry.png'),'image/png');
$('trace').onclick=()=>download(new Blob([JSON.stringify(runHistory,null,2)],{type:'application/json'}),name+'-physics-trace.json');
try{const response=await fetch('./park-group.jpg');if(!response.ok)throw new Error('Could not load sample. Choose a photo.');await open(await response.blob(),'park-group.jpg');}catch(e){$('status').textContent=e.message;}
