'use strict';

// Art is sampled from the approved PNG; transforms never regenerate its curves.
const sharp = require('sharp');
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const { states, looks } = require('./poses.cjs');
const ROOT = path.resolve(__dirname, '..');
const WORLD = 768, CELL_W = 192, CELL_H = 208, SCALE = 0.235;
const sha = data => crypto.createHash('sha256').update(data).digest('hex');

async function sourceLayers() {
  const original = await fs.readFile(path.join(ROOT, 'assets/reference.png'));
  const {data} = await sharp(original).resize(WORLD,WORLD).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  const n=WORLD*WORLD, outside=Buffer.alloc(n), queue=new Int32Array(n);
  let head=0,tail=0;
  function add(p){
    if(outside[p])return;
    const i=p*4;
    if(data[i+3]<8 || Math.min(data[i],data[i+1],data[i+2])>224){outside[p]=1;queue[tail++]=p;}
  }
  for(let x=0;x<WORLD;x++){add(x);add((WORLD-1)*WORLD+x);}
  for(let y=0;y<WORLD;y++){add(y*WORLD);add(y*WORLD+WORLD-1);}
  while(head<tail){
    const p=queue[head++],x=p%WORLD,y=Math.floor(p/WORLD);
    if(x)add(p-1);if(x<WORLD-1)add(p+1);if(y)add(p-WORLD);if(y<WORLD-1)add(p+WORLD);
  }
  // Only flood-connected exterior white is removed. Enclosed belly and eye
  // whites stay opaque. Unmatte colored edges too: a white fringe around the
  // scarf becomes conspicuous when a moving flipper passes behind that edge.
  const full=Buffer.from(data);
  for(let p=0;p<n;p++){
    const i=p*4;
    if(outside[p]){full.fill(0,i,i+4);continue;}
    const x=p%WORLD,y=Math.floor(p/WORLD);
    const lo=Math.min(data[i],data[i+1],data[i+2]),hi=Math.max(data[i],data[i+1],data[i+2]);
    let edge=false;
    if(hi>0)for(let oy=-2;oy<=2&&!edge;oy++)for(let ox=-2;ox<=2;ox++){
      if(x+ox>=0&&x+ox<WORLD&&y+oy>=0&&y+oy<WORLD&&outside[(y+oy)*WORLD+x+ox]){edge=true;break;}
    }
    if(edge && hi-lo<18){full[i]=full[i+1]=full[i+2]=0;full[i+3]=255-Math.round((data[i]+data[i+1]+data[i+2])/3);}
    else if(edge){
      let nearest=null,distance=Infinity;
      for(let oy=-6;oy<=6;oy++)for(let ox=-6;ox<=6;ox++){
        const nx=x+ox,ny=y+oy,d=ox*ox+oy*oy;
        if(d>=distance||nx<2||ny<2||nx>=WORLD-2||ny>=WORLD-2)continue;
        let interior=true;
        for(let yy=-2;yy<=2&&interior;yy++)for(let xx=-2;xx<=2;xx++){
          if(outside[(ny+yy)*WORLD+nx+xx]){interior=false;break;}
        }
        if(interior){nearest=(ny*WORLD+nx)*4;distance=d;}
      }
      if(nearest!==null){
        let numerator=0,denominator=0;
        for(let channel=0;channel<3;channel++){
          const foreground=255-data[nearest+channel];
          numerator+=(255-data[i+channel])*foreground;denominator+=foreground*foreground;
        }
        const alpha=denominator?Math.max(0,Math.min(1,numerator/denominator)):1;
        for(let channel=0;channel<3;channel++)full[i+channel]=alpha?Math.max(0,Math.min(255,Math.round((data[i+channel]-255*(1-alpha))/alpha))):0;
        full[i+3]=Math.round(full[i+3]*alpha);
      }
    }
  }
  const layers=Object.fromEntries(['body','leftArm','rightArm','feet','scarf','eyes','pupils','beak'].map(k=>[k,Buffer.alloc(full.length)]));
  layers.body.set(full);
  const copy=(target,i)=>full.copy(layers[target],i,i,i+4);
  const erase=i=>layers.body.fill(0,i,i+4);
  const black=i=>{layers.body[i]=layers.body[i+1]=layers.body[i+2]=0;};
  for(let y=0;y<WORLD;y++)for(let x=0;x<WORLD;x++){
    const i=(y*WORLD+x)*4,r=full[i],g=full[i+1],b=full[i+2];
    if(!full[i+3])continue;
    const red=r>g*1.6 && r>b*1.8 && r>75;
    const orange=r>130 && g>75 && g<r*.9 && b<g*.9;
    const dark=Math.max(r,g,b)<235 && Math.max(r,g,b)-Math.min(r,g,b)<25;
    if(y>=350 && y<595 && dark){
      const edgeX=y<552 ? 143-(y-350)*.14 : 115;
      const jointOverlap=22*Math.max(0,Math.min(1,(550-y)/80));
      if(x<edgeX+jointOverlap)copy('leftArm',i);
      if(x>WORLD-edgeX-jointOverlap)copy('rightArm',i);
      // Round the hidden armpit into the existing torso instead of exposing
      // the source's sharp wing/body junction when the flipper is lifted.
      const torsoEdge=107+.0016*(y-475)**2;
      const coverage=Math.max(0,Math.min(1,Math.min(x-torsoEdge,WORLD-torsoEdge-x)+.5));
      layers.body[i+3]=Math.round(layers.body[i+3]*coverage);
    }
    if(y>641 && orange){copy('feet',i);erase(i);}
    if(y>394 && y<507 && x>162 && x<278 && red){
      copy('scarf',i);
      if(y>405){layers.body[i]=layers.body[i+1]=layers.body[i+2]=255;}
    }
    // The original eye patches are retained, including their antialiasing.
    const eye=(x>=270&&x<=354&&y>=134&&y<=222)||(x>=407&&x<=493&&y>=134&&y<=222);
    if(eye){
      copy('eyes',i);black(i);
      const pupil=(x>=295&&x<=331&&y>=159&&y<=199)||(x>=432&&x<=468&&y>=159&&y<=199);
      if(pupil){
        layers.pupils[i+3]=255-Math.min(r,g,b);
        layers.eyes[i]=layers.eyes[i+1]=layers.eyes[i+2]=255;
      }
    }
    if(x>=237&&x<=526&&y>=242&&y<=339){copy('beak',i);black(i);}
  }
  // Closed lids follow the original lower eye arcs, rather than flattening
  // the pupils into slits. The pupil stays fully hidden during the blink.
  layers.closedEyes=Buffer.alloc(full.length);
  for(let y=195;y<=220;y++)for(let x=268;x<=496;x++){
    if(x>357&&x<405)continue;
    const i=(y*WORLD+x)*4;
    let inner=255;
    for(let oy=-5;oy<=5;oy+=2)for(let ox=-5;ox<=5;ox+=2){
      const j=((y+oy)*WORLD+x+ox)*4;
      inner=Math.min(inner,layers.eyes[j],layers.eyes[j+1],layers.eyes[j+2]);
    }
    const a=Math.max(0,Math.min(layers.eyes[i],layers.eyes[i+1],layers.eyes[i+2])-inner);
    const j=((y-29)*WORLD+x)*4;
    layers.closedEyes[j]=layers.closedEyes[j+1]=layers.closedEyes[j+2]=255;layers.closedEyes[j+3]=a;
  }
  const encoded={};
  await fs.mkdir(path.join(ROOT,'work/refinement/layers'),{recursive:true});
  for(const [name,buffer]of Object.entries({...layers,full})){
    const png=await sharp(buffer,{raw:{width:WORLD,height:WORLD,channels:4}}).png().toBuffer();
    encoded[name]=`data:image/png;base64,${png.toString('base64')}`;
    await fs.writeFile(path.join(ROOT,`work/refinement/layers/${name}.png`),png);
  }
  return {encoded,rawLayers:layers,sourceHash:sha(original)};
}

const smooth=(value)=>{const t=Math.max(0,Math.min(1,value));return t*t*(3-2*t);};
function rotated(x,y,pivotX,pivotY,angle,dx=0,dy=0){
  const radians=angle*Math.PI/180,c=Math.cos(radians),s=Math.sin(radians);
  const u=x-pivotX,v=y-pivotY;
  return [pivotX+c*u-s*v+dx,pivotY+s*u+c*v+dy];
}

// Warp a connected texture with a shared triangle mesh. Sampling premultiplied
// colors keeps the semitransparent edge free of dark seams.
async function warpLayer(raw,bounds,deform){
  const out=Buffer.alloc(raw.length);
  const map=(x,y)=>[...deform(x,y),x,y];
  function triangle(a,b,c){
    const det=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1]);
    if(Math.abs(det)<.01)return;
    const minX=Math.max(0,Math.floor(Math.min(a[0],b[0],c[0]))),maxX=Math.min(WORLD-1,Math.ceil(Math.max(a[0],b[0],c[0])));
    const minY=Math.max(0,Math.floor(Math.min(a[1],b[1],c[1]))),maxY=Math.min(WORLD-1,Math.ceil(Math.max(a[1],b[1],c[1])));
    for(let y=minY;y<=maxY;y++)for(let x=minX;x<=maxX;x++){
      const u=((b[1]-c[1])*(x+.5-c[0])+(c[0]-b[0])*(y+.5-c[1]))/det;
      const v=((c[1]-a[1])*(x+.5-c[0])+(a[0]-c[0])*(y+.5-c[1]))/det,w=1-u-v;
      if(u<-.001||v<-.001||w<-.001)continue;
      const sx=u*a[2]+v*b[2]+w*c[2]-.5,sy=u*a[3]+v*b[3]+w*c[3]-.5;
      const ix=Math.floor(sx),iy=Math.floor(sy),fx=sx-ix,fy=sy-iy;
      if(ix<0||iy<0||ix>=WORLD-1||iy>=WORLD-1)continue;
      const offsets=[(iy*WORLD+ix)*4,(iy*WORLD+ix+1)*4,((iy+1)*WORLD+ix)*4,((iy+1)*WORLD+ix+1)*4];
      const weights=[(1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy];
      const alpha=offsets.reduce((sum,p,k)=>sum+raw[p+3]*weights[k],0);
      const target=(y*WORLD+x)*4;
      if(alpha<=out[target+3])continue;
      for(let channel=0;channel<3;channel++)out[target+channel]=Math.round(offsets.reduce((sum,p,k)=>sum+raw[p+channel]*raw[p+3]*weights[k],0)/alpha);
      out[target+3]=Math.round(alpha);
    }
  }
  const [minX,minY,maxX,maxY]=bounds,step=4;
  for(let y=minY;y<maxY;y+=step)for(let x=minX;x<maxX;x+=step){
    const a=map(x,y),b=map(Math.min(x+step,maxX),y),c=map(x,Math.min(y+step,maxY)),d=map(Math.min(x+step,maxX),Math.min(y+step,maxY));
    triangle(a,b,c);triangle(b,d,c);
  }
  const png=await sharp(out,{raw:{width:WORLD,height:WORLD,channels:4}}).png().toBuffer();
  return `data:image/png;base64,${png.toString('base64')}`;
}

// Keep shoulders behind the torso and scarf; only the bent distal flipper
// crosses in front. Both depth layers use exactly the same deformation.
async function bendArm(raw,side,angle,dx,dy){
  const pivotX=side==='left'?125:644;
  const bounds=side==='left'?[32,344,182,600]:[586,344,736,600];
  const thinking=side==='right'&&angle>70;
  const deform=(x,y)=>{
    if(thinking){
      // Route the thinking flipper around the outside of the scarf. A blended
      // rigid turn folds the shaft through the red band, leaving a red shard.
      const phase=Math.max(0,Math.min(1,(angle-96)/26));
      const t=Math.max(0,Math.min(1,(y-350)/235)),u=1-t;
      const points=[[636,356],[650,438],[770,250-phase*24],[534-phase*28,320-phase*25]];
      const center=[0,1].map(axis=>u*u*u*points[0][axis]+3*u*u*t*points[1][axis]+3*u*t*t*points[2][axis]+t*t*t*points[3][axis]);
      const tangent=[0,1].map(axis=>3*u*u*(points[1][axis]-points[0][axis])+6*u*t*(points[2][axis]-points[1][axis])+3*t*t*(points[3][axis]-points[2][axis]));
      const length=Math.hypot(...tangent),offset=x-(644+(y-365)*.22);
      return [center[0]+offset*tangent[1]/length,center[1]-offset*tangent[0]/length];
    }
    // Keep the shoulder tangent fixed and spread ordinary bending to the tip.
    const w=smooth((y-350)/235);
    if(Math.abs(angle)<70)return rotated(x,y,pivotX,365,angle*w,dx*w,dy*w);
    // The high wave bends earlier so its raised tip stays inside its cell.
    const target=rotated(x,y,pivotX,365,angle,dx,dy),raise=smooth((y-350)/92);
    return [x+raise*(target[0]-x),y+raise*(target[1]-y)];
  };
  const result={};
  if(angle||dx||dy)result[side+'Arm']=await warpLayer(raw,bounds,deform);
  if(thinking){
    const tip=Buffer.from(raw);
    for(let y=344;y<442;y++)for(let x=bounds[0];x<bounds[2];x++){
      const i=(y*WORLD+x)*4;tip[i+3]=Math.round(tip[i+3]*smooth((y-398)/4));
    }
    result[side+'ArmFront']=await warpLayer(tip,bounds,deform);
  }
  return result;
}

async function bendFeet(raw,p){
  if(!['left','right'].some(side=>p[side+'FootRotate']||p[side+'FootX']||p[side+'FootY']))return null;
  return warpLayer(raw,[180,640,586,736],(x,y)=>{
    const left=rotated(x,y,290,700,p.leftFootRotate,p.leftFootX,p.leftFootY);
    const right=rotated(x,y,479,700,p.rightFootRotate,p.rightFootX,p.rightFootY);
    const w=smooth((x-326)/116);
    return [left[0]*(1-w)+right[0]*w,left[1]*(1-w)+right[1]*w];
  });
}

async function bendScarf(raw,angle){
  if(!angle)return null;
  return warpLayer(raw,[160,392,280,512],(x,y)=>{
    const target=rotated(x,y,228,400,angle),w=smooth((y-405)/72);
    return [x+w*(target[0]-x),y+w*(target[1]-y)];
  });
}

function markup(layers,p,neutral=false){
  const img=name=>`<image href="${layers[name]}" x="0" y="0" width="768" height="768"/>`;
  const eyeScale=Math.max(.15,1-p.blink*.8);
  const eyes=p.blink>.7 ? img('closedEyes') : `<g transform="translate(0 178) scale(1 ${eyeScale}) translate(0 -178)">${img('eyes')}<g transform="translate(${p.gazeX} ${p.gazeY})">${img('pupils')}</g></g>`;
  const face=`<g transform="rotate(${p.headRotate} 384 279)">${eyes}<g transform="translate(${p.gazeX*.2} ${p.gazeY*.24})">${img('beak')}</g></g>`;
  const frontRight=p.rightArmRotate>70;
  const body=neutral?img('full'):
    `${img('feet')}${img('leftArm')}${img('rightArm')}${img('body')}${img('scarf')}${face}${frontRight?img('rightArmFront'):''}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="768" height="832" viewBox="0 0 192 208"><g transform="translate(96 196) scale(${SCALE}) translate(-384 -718)"><g transform="translate(0 ${p.bodyY}) translate(384 410) rotate(${p.bodyRotate}) scale(${p.bodyScaleX} ${p.bodyScaleY}) translate(-384 -410)">${body}</g></g></svg>`;
}

async function build(){
  const {encoded,rawLayers,sourceHash}=await sourceLayers();
  const metaPath=path.join(ROOT,'assets/pet.json');
  const metadata=JSON.parse(await fs.readFile(metaPath,'utf8'));
  if(states.length!==9 || looks.length!==16 || states.some((s,i)=>s.name!==metadata.states[i].name||s.frames.length!==metadata.states[i].frames))throw new Error('Pose definitions do not match the v2 atlas.');
  const cells=[],report=[];
  for(let row=0;row<11;row++){
    const poses=row<9?states[row].frames:looks.slice((row-9)*8,(row-8)*8);
    for(let col=0;col<poses.length;col++){
      const pose=poses[col],frameLayers={...encoded};
      for(const side of ['left','right']){
        Object.assign(frameLayers,await bendArm(rawLayers[side+'Arm'],side,pose[side+'ArmRotate'],pose[side+'ArmX'],pose[side+'ArmY']));
      }
      const feet=await bendFeet(rawLayers.feet,pose),scarf=await bendScarf(rawLayers.scarf,pose.scarfRotate);
      if(feet)frameLayers.feet=feet;
      if(scarf)frameLayers.scarf=scarf;
      const raster=await sharp(Buffer.from(markup(frameLayers,pose,row===0&&col===0))).resize(CELL_W,CELL_H).ensureAlpha().raw().toBuffer();
      let left=CELL_W,top=CELL_H,right=0,bottom=0,count=0;
      for(let y=0;y<CELL_H;y++)for(let x=0;x<CELL_W;x++){
        const i=(y*CELL_W+x)*4;
        if(!raster[i+3]){raster[i]=raster[i+1]=raster[i+2]=0;continue;}
        count++;left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x+1);bottom=Math.max(bottom,y+1);
      }
      if(left===0||top===0||right===CELL_W||bottom===CELL_H)throw new Error(`Clipped pose ${row},${col}: ${[left,top,right,bottom]}`);
      const png=await sharp(raster,{raw:{width:CELL_W,height:CELL_H,channels:4}}).png().toBuffer();
      cells.push({input:png,left:col*CELL_W,top:row*CELL_H});
      report.push({state:row<9?states[row].name:'look',row,column:col,bounds:[left,top,right,bottom],nontransparent_pixels:count});
    }
  }
  const atlas=await sharp({create:{width:1536,height:2288,channels:4,background:{r:0,g:0,b:0,alpha:0}}}).composite(cells).png().toBuffer();
  await fs.writeFile(path.join(ROOT,'assets/spritesheet.png'),atlas);
  metadata.spritesheet.sha256=sha(atlas);
  metadata.source={image:'reference.png',sha256:sourceHash,method:'Direct pixel layers and deterministic transforms; no generated animation frames.'};
  await fs.writeFile(metaPath,JSON.stringify(metadata,null,2)+'\n');
  await fs.writeFile(path.join(ROOT,'qa/generation-validation.json'),JSON.stringify({
    ok:true,source:'assets/reference.png',source_sha256:sourceHash,sha256:sha(atlas),
    method:metadata.source.method,scale:SCALE,neutral_source_pose:[0,0],cells:report
  },null,2)+'\n');
  console.log(JSON.stringify({ok:true,frames:report.length,sha256:sha(atlas),source_sha256:sourceHash}));
}

build().catch(error=>{console.error(error.message);process.exitCode=1;});
