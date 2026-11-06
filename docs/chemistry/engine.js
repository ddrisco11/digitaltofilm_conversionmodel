// Actual spectral exposure, latent grain sampling and two reaction–diffusion baths.
export function randomGenerator(seed) {
  return () => {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t ^= t + Math.imul(t ^ t >>> 7, 61 | t);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
const gamma4 = x => Math.max(0, 1-Math.exp(-x)*(1+x+x*x/2+x*x*x/6));
const srgb = x => Math.round(255*(x<=.0031308 ? 12.92*Math.max(0,x) : 1.055*Math.min(1,x)**(1/2.4)-.055));
const linear = x => x<=.04045 ? x/12.92 : ((x+.055)/1.055)**2.4;
const dot = (a, m, j) => a[0]*m[0][j]+a[1]*m[1][j]+a[2]*m[2][j];

function binomial(n,p,rng) {
  if(p<=0)return 0;
  if(p>=1)return n;
  const reverse=p>.5;
  if(reverse)p=1-p;
  let probability=(1-p)**n, sum=probability, k=0;
  const u=rng();
  while(u>sum && k<n) {
    probability*=((n-k)/(k+1))*(p/(1-p));
    sum+=probability; k++;
  }
  return reverse?n-k:k;
}

function diffuse(a,out,w,h) {
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    const i=y*w+x;
    out[i]=a[(y?y-1:y)*w+x]+a[(y<h-1?y+1:y)*w+x]
      +a[y*w+(x?x-1:x)]+a[y*w+(x<w-1?x+1:x)]-4*a[i];
  }
}

function chemistry(active,w,h,steps,bath,phase,channel,probe,update) {
  const n=active.length;
  const dev=new Float32Array(n).fill(1),silver=new Float32Array(n);
  const ox=new Float32Array(n),coupler=new Float32Array(n).fill(1);
  const dye=new Float32Array(n),lap=new Float32Array(n);
  for(let step=0;step<steps;step++) {
    diffuse(dev,lap,w,h);
    for(let i=0;i<n;i++){
      dev[i]+=.4*(.15*lap[i]+bath*(1-dev[i]));
      const amount=Math.min(dev[i],(active[i]-silver[i])*(-Math.expm1(-.13*.4*dev[i])));
      dev[i]-=amount; silver[i]+=amount; ox[i]+=amount;
    }
    diffuse(ox,lap,w,h);
    for(let i=0;i<n;i++){
      ox[i]+=.4*.18*lap[i];
      const formed=Math.min(coupler[i],ox[i]*(-Math.expm1(-.7*.4*coupler[i])));
      ox[i]=(ox[i]-formed)*Math.exp(-.03*.4);
      dye[i]+=formed; coupler[i]-=formed;
    }
    if(step%5===0 || step===steps-1)update({
      phase,channel,step:step+1,steps,time:(step+1)*.4,
      developer:dev[probe],silver:silver[probe],oxidized:ox[probe],
      coupler:coupler[probe],dye:dye[probe],active:active[probe]
    });
  }
  return dye;
}

export function simulate(pixels,w,h,model,seed,probe,update=()=>{}) {
  const n=w*h, rng=randomGenerator(seed);
  const film=Array.from({length:3},()=>new Float32Array(n));
  const paper=Array.from({length:3},()=>new Float32Array(n));
  const phases=Array.from({length:4},()=>rng()*2*Math.PI);
  let exposureProbe;
  for(let i=0;i<n;i++){
    const rgb=[linear(pixels[i*4]/255),linear(pixels[i*4+1]/255),linear(pixels[i*4+2]/255)];
    const drive=[0,1,2].map(c=>Math.max(0,Math.min(1,dot(rgb,model.drive,c))));
    const x=i%w,y=Math.floor(i/w);
    const variation=1+.0075*(Math.sin(x/11+phases[0])*Math.sin(y/13+phases[1])
                           +Math.sin(x/23+phases[2])*Math.sin(y/19+phases[3]));
    const exposure=[0,1,2].map(c=>dot(drive,model.expose,c)*variation);
    if(i===probe)exposureProbe=exposure;
    for(let c=0;c<3;c++){
      let active=0,total=0;
      for(let j=0;j<24;j++){
        const u=rng(), radius=u<.4?.75:u<.8?1:1.35;
        const speed=[2,10,50][Math.floor(rng()*3)],mass=radius**3;
        total+=mass;
        if(rng()<gamma4(exposure[c]*speed*radius*radius))active+=mass;
      }
      film[c][i]=active/total;
    }
    if(i%Math.max(1,w*32)===0)update({phase:'exposure',fraction:i/n});
  }
  update({phase:'exposure',fraction:1,exposure:exposureProbe});
  for(let c=0;c<3;c++)film[c]=chemistry(film[c],w,h,45,.11,'film',c,probe,update);
  const negative=new Uint8ClampedArray(n*4);
  for(let i=0;i<n;i++){
    const rgb=[0,0,0],light=[0,0,0];
    for(let k=0;k<model.wavelengths.length;k++){
      const d=model.filmDyes[k];
      const t=10**(-.1-2*(film[0][i]*d[0]+film[1][i]*d[1]+film[2][i]*d[2]));
      for(let c=0;c<3;c++){
        light[c]+=t*model.response[k][c]*.35;
        rgb[c]+=t*model.viewer[k][c];
      }
    }
    for(let c=0;c<3;c++){
      let count=0;
      for(const speed of [12,30,75])count+=binomial(128,gamma4(light[c]*speed),rng);
      paper[c][i]=count/384;
      negative[4*i+c]=srgb(rgb[c]);
    }
    negative[4*i+3]=255;
    if(i%Math.max(1,w*32)===0)update({phase:'paper-exposure',fraction:i/n});
    if(i===probe)update({phase:'negative',filmDyes:film.map(a=>a[i]),paperExposure:light});
  }
  update({phase:'negative-image',pixels:negative});
  for(let c=0;c<3;c++)paper[c]=chemistry(paper[c],w,h,55,.14,'paper',c,probe,update);
  const output=new Uint8ClampedArray(n*4),spectrum=[];
  for(let i=0;i<n;i++){
    const rgb=[0,0,0];
    for(let k=0;k<model.wavelengths.length;k++){
      const d=model.paperDyes[k],scatter=.01;
      const absorption=.008+3.7*(paper[0][i]*d[0]+paper[1][i]*d[1]+paper[2][i]*d[2]);
      const g=Math.sqrt(absorption*(absorption+2*scatter)),u=Math.sinh(g)/g;
      const den=Math.cosh(g)+(absorption+scatter)*u,r=scatter*u/den,t=1/den;
      const reflectance=r+t*t*.94/(1-r*.94);
      for(let c=0;c<3;c++)rgb[c]+=reflectance*model.viewer[k][c];
      if(i===probe)spectrum.push(reflectance);
    }
    for(let c=0;c<3;c++)output[4*i+c]=srgb(rgb[c]);
    output[4*i+3]=255;
    if(i%Math.max(1,w*32)===0)update({phase:'reflection',fraction:i/n});
  }
  update({phase:'spectrum',spectrum,wavelengths:model.wavelengths});
  return output;
}
