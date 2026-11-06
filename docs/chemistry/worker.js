import {simulate} from './engine.js?v=scan-b-1';
self.onmessage=async({data})=>{
  try{
    const response=await fetch('./model.json');
    if(!response.ok)throw new Error('Could not load the spectral material data.');
    const model=await response.json();
    const pixels=simulate(data.pixels,data.width,data.height,model,data.seed,data.probe,
      state=>self.postMessage({type:'progress',...state}),data.profile);
    self.postMessage({type:'complete',pixels},[pixels.buffer]);
  }catch(error){self.postMessage({type:'error',message:error.message});}
};
