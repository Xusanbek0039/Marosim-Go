import * as THREE from 'three';
import { RoomEnvironment } from './vendor/RoomEnvironment.js';

document.body.classList.toggle('overview',new URLSearchParams(location.search).has('overview'));

const concepts = [
  ['Mercury', 'Simob yadrosi', 'Bir tomchi metall tirik organizmdek uradi. Katta, dadil va organik hero vizual.', 'MORPHING CHROME'],
  ['Tension', 'Taranglik', 'Cho‘zilib, burilib, yana yig‘iladigan metall membrana. Silliq yuzada keskin yorug‘lik.', 'CHROME MEMBRANE'],
  ['Ferro', 'Magnit maydon', 'Magnit kuchiga javob berayotgandek ko‘tariladigan metall tikanlar. Kuchli texnologik xarakter.', 'FERROFLUID'],
  ['Liquid knot', 'Suyuq rishta', 'Og‘ir metall tugun uzluksiz oqadi. Harakatda o‘zgaradigan chuqur reflekslar.', 'TOPOLOGICAL METAL'],
  ['Collision', 'To‘qnashuv', 'Yirik xrom tomchilar markazga yig‘iladi va yana tarqaladi. Ritmik, dinamik kompozitsiya.', 'ORBITAL DROPLETS'],
  ['Chrome silk', 'Xrom ipak', 'Shamolda egiladigan yaltiroq metall mato. Keng, to‘lqinli va yengil harakat.', 'METALLIC CLOTH'],
  ['Supernova', 'Portlash', 'Markazdan o‘sib chiqadigan oltin-xrom nurlar. Bir ochilib, bir yig‘iladigan kuchli siluet.', 'KINETIC SCULPTURE'],
  ['Soft block', 'Yumshoq monolit', 'Qattiq kub suyuq jismga aylanadi. Og‘ir shakl va elastik harakat o‘rtasidagi o‘yin.', 'ELASTIC SOLID'],
  ['Vortex', 'Metall girdob', 'O‘nlab metall pichoqlar spiral bo‘lib ochiladi. Kamera qarshisida oqadigan mexanik xoreografiya.', 'CHOREOGRAPHED BLADES'],
  ['Continuum', 'Vaqt oqimi', 'Markazidan siqilib, ikki tomonga oqadigan suyuq metall. Qumsoatning abstrakt talqini.', 'LIQUID HOURGLASS'],
];
const gallery = document.getElementById('gallery');
concepts.forEach(([name,title,description,material], i) => {
  const card = document.createElement('article'); card.className = 'card'; card.id = `concept-${i+1}`;
  card.innerHTML = `<div class="stage"><span class="id"><strong>${String(i+1).padStart(2,'0')}</strong> / ${name.toUpperCase()}</span><span class="material">${material}</span><canvas aria-label="${i+1}. ${title}, jonli 3D"></canvas><span class="stage-note">PHYSICAL REFLECTIONS / LIVE MOTION</span><span class="loading">3D tayyorlanmoqda…</span></div><div class="caption"><div><h2>${title}</h2><p>${description}</p></div><button type="button" class="pick" aria-label="${i+1}-variantni tanlash" aria-pressed="false">↗</button></div>`;
  gallery.append(card);
  card.querySelector('.pick').addEventListener('click', () => {
    document.querySelectorAll('.card').forEach((item,j) => { item.classList.toggle('selected',i===j);item.querySelector('.pick').setAttribute('aria-pressed',String(i===j)); });
    document.getElementById('selection').innerHTML = `Tanlandi: <b>${String(i+1).padStart(2,'0')} — ${title}</b>. Raqamini menga yozing.`;
    try { localStorage.setItem('mg-liquid-choice',String(i+1)); } catch {}
  });
});
const error = document.getElementById('error');
function fail(message) { error.hidden=false; error.textContent=message; document.querySelectorAll('.loading').forEach(e=>e.textContent='3D yuklanmadi'); }
let renderer;
try { renderer = new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'}); }
catch { fail('WebGL ishga tushmadi. Brauzerda apparat tezlashtirishni yoqing yoki Chrome / Edge’da oching.'); }
if (renderer) {
try {
renderer.setPixelRatio(Math.min(devicePixelRatio || 1,1.7));
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.45;
const pmrem = new THREE.PMREMGenerator(renderer), room = new RoomEnvironment();
const environment = pmrem.fromScene(room,0.04).texture; room.dispose(); pmrem.dispose();
const chrome = new THREE.MeshPhysicalMaterial({color:0xe2e3eb,metalness:1,roughness:0.17,clearcoat:1,clearcoatRoughness:0.1,envMapIntensity:1.15});
const platinum = chrome.clone(); platinum.color.set(0xa8b4d3); platinum.roughness=0.21;
const warm = chrome.clone(); warm.color.set(0xd4ac72); warm.roughness=0.2;
const pearl = chrome.clone(); pearl.color.set(0xbec8f1); pearl.roughness=0.13;
const TAU=Math.PI*2;
function mesh(geometry,material=chrome) { return new THREE.Mesh(geometry,material); }
function deformer(geometry, fn) {
  const attribute=geometry.attributes.position, base=attribute.array.slice();
  return t=>{for(let i=0;i<attribute.count;i++){const p=fn(base[i*3],base[i*3+1],base[i*3+2],t);attribute.setXYZ(i,...p);}attribute.needsUpdate=true;geometry.computeVertexNormals();};
}
function sphere(radius=1) {return new THREE.SphereGeometry(radius,64,40);}
class KnotCurve extends THREE.Curve {
  getPoint(t,target=new THREE.Vector3()) {const a=t*TAU,r=0.7+0.21*Math.cos(3*a);return target.set(r*Math.cos(2*a),r*Math.sin(2*a),0.35*Math.sin(3*a));}
}
function roundedBox(){
  const s=new THREE.Shape(),r=.2,h=.66;
  s.moveTo(-h+r,-h);s.lineTo(h-r,-h);s.quadraticCurveTo(h,-h,h,-h+r);s.lineTo(h,h-r);s.quadraticCurveTo(h,h,h-r,h);s.lineTo(-h+r,h);s.quadraticCurveTo(-h,h,-h,h-r);s.lineTo(-h,-h+r);s.quadraticCurveTo(-h,-h,-h+r,-h);
  const g=new THREE.ExtrudeGeometry(s,{depth:.95,bevelEnabled:true,bevelSegments:6,steps:12,bevelSize:.16,bevelThickness:.16,curveSegments:8});g.center();return g;
}
const builders = [
 group=>{
  const g=sphere(),body=mesh(g);group.add(body);
  const deform=deformer(g,(x,y,z,t)=>{const r=1+.13*Math.sin(3*x+t*.9)*Math.cos(3*y-t*.6)+.09*Math.sin(4*z+t*.5)+.05*Math.sin(y*6+x*2-t);return [x*r,y*r,z*r];});
  return t=>{deform(t);body.rotation.set(t*.12,t*.2,Math.sin(t*.4)*.12);};
 },
 group=>{
  const g=new THREE.TorusGeometry(.8,.27,24,100),body=mesh(g,platinum);group.add(body);
  const deform=deformer(g,(x,y,z,t)=>{const a=Math.atan2(y,x),twist=Math.sin(a*3+t*.7);return [x*(1+.13*Math.sin(t*.6)),y*(1-.13*Math.sin(t*.6)),z+.27*twist];});
  return t=>{deform(t);body.rotation.set(.4+Math.sin(t*.3)*.25,t*.2,t*.08);};
 },
 group=>{
  const g=new THREE.SphereGeometry(.84,104,64),body=mesh(g,platinum);group.add(body);
  const deform=deformer(g,(x,y,z,t)=>{const r=Math.hypot(x,y,z),theta=Math.atan2(z,x),phi=Math.acos(Math.max(-1,Math.min(1,y/r))),peaks=Math.pow(Math.max(0,Math.cos(theta*12+t*.3)*Math.sin(phi*11-t*.4)),5),k=1+peaks*.65;return[x*k,y*k,z*k];});
  return t=>{deform(t);body.rotation.set(.2,t*.14,.15);};
 },
 group=>{
  const g=new THREE.TubeGeometry(new KnotCurve(),160,.16,14,true),body=mesh(g);group.add(body);
  const deform=deformer(g,(x,y,z,t)=>[x*(1+.06*Math.sin(t+y*2)),y*(1+.08*Math.cos(t*.7+x*3)),z+.07*Math.sin(x*3+y*2+t)]);
  return t=>{deform(t);body.rotation.set(.35+Math.sin(t*.25)*.25,t*.19,t*.1);};
 },
 group=>{
  const drops=Array.from({length:7},(_,i)=>{const body=mesh(sphere(i===0?.49:.24+(i%3)*.07),i%3===0?warm:chrome);group.add(body);return body;});
  return t=>{drops.forEach((drop,i)=>{if(!i){drop.scale.setScalar(1+Math.sin(t*1.2)*.08);return;}const a=i/6*TAU+t*.35,r=.64+.26*Math.sin(t*.8+i*.7);drop.position.set(Math.cos(a)*r,Math.sin(a)*r*.85,Math.sin(a*2+t*.3)*.35);drop.scale.set(1+.13*Math.sin(t+i),1-.1*Math.sin(t+i),1);});group.rotation.y=Math.sin(t*.25)*.6;};
 },
 group=>{
  const g=new THREE.PlaneGeometry(1.95,1.95,64,64),material=pearl.clone();material.side=THREE.DoubleSide;
  const body=mesh(g,material);group.add(body);
  const deform=deformer(g,(x,y,z,t)=>[x+.09*Math.sin(y*3+t*.8),y+.08*Math.sin(x*4-t*.6),.23*Math.sin(x*3+y*2+t*.7)+.15*Math.cos(y*4-t*.8)]);
  return t=>{deform(t);body.rotation.set(-.25+Math.sin(t*.3)*.18,Math.sin(t*.3)*.5,-.35);};
 },
 group=>{
  const rays=Array.from({length:26},(_,i)=>{const body=mesh(new THREE.ConeGeometry(.12,.82,7,1),i%4===0?warm:chrome),y=1-2*(i+.5)/26,a=i*2.399963,d=new THREE.Vector3(Math.sqrt(1-y*y)*Math.cos(a),y,Math.sqrt(1-y*y)*Math.sin(a));body.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),d);group.add(body);return{body,d};});group.add(mesh(sphere(.36),warm));
  return t=>{rays.forEach(({body,d},i)=>{const pulse=.5+.5*Math.sin(t*.95+i*.22);body.position.copy(d).multiplyScalar(.54+pulse*.17);body.scale.set(.7+pulse*.3,.65+pulse*.55,.7+pulse*.3);});group.rotation.set(t*.1,t*.18,0);};
 },
 group=>{
  const g=roundedBox(),body=mesh(g);group.add(body);
  const deform=deformer(g,(x,y,z,t)=>{const a=y*.45*Math.sin(t*.65),c=Math.cos(a),s=Math.sin(a),pulse=.07*Math.sin(y*4+t);return[(x*c-z*s)*(1+pulse),y*(1-.08*Math.sin(t*.65)),(x*s+z*c)*(1+pulse)];});
  return t=>{deform(t);body.rotation.set(.5+Math.sin(t*.3)*.15,t*.23,.2);};
 },
 group=>{
  const blades=Array.from({length:36},(_,i)=>{const body=mesh(new THREE.BoxGeometry(.06,.38,.28),i%5===0?warm:platinum);group.add(body);return body;});
  return t=>{blades.forEach((body,i)=>{const a=i/36*TAU+t*.23,wave=Math.sin(i/36*TAU*3-t*.85),r=.76+wave*.12;body.position.set(Math.cos(a)*r,Math.sin(a)*r,wave*.24);body.rotation.set(a*.3+t*.1,wave*.7,a+.4);});group.rotation.set(.3,Math.sin(t*.25)*.5,0);};
 },
 group=>{
  const points=Array.from({length:65},(_,i)=>{const y=(i/64-.5)*2.1,r=.16+.65*Math.pow(Math.abs(y)/1.05,1.3);return new THREE.Vector2(r,y);});
  const g=new THREE.LatheGeometry(points,80),body=mesh(g,pearl);group.add(body);
  const deform=deformer(g,(x,y,z,t)=>{const a=Math.atan2(z,x),r=1+.07*Math.sin(y*6-t*1.1)+.06*Math.cos(a*5+y*3+t*.5);return[x*r,y,z*r];});
  return t=>{deform(t);body.rotation.set(.08,t*.2,Math.sin(t*.3)*.12);};
 },
];
const views = [...document.querySelectorAll('.card')].map((card,i)=>{
  const canvas=card.querySelector('canvas'),scene=new THREE.Scene();scene.background=new THREE.Color(0x111116);scene.environment=environment;
  const camera=new THREE.PerspectiveCamera(35,1,.1,30);camera.position.set(0,0,5.3);
  const group=new THREE.Group();scene.add(group);
  const key=new THREE.DirectionalLight(0xffffff,3);key.position.set(-3,4,5);scene.add(key);
  const rim=new THREE.PointLight(i%2?0xabc2ff:0xcad8ff,22,10);rim.position.set(3,1,-1);scene.add(rim);
  const accent=new THREE.PointLight(0xd6ff85,7,10);accent.position.set(-3,-1,1);scene.add(accent);
  const update=builders[i](group),view={card,canvas,ctx:canvas.getContext('2d'),scene,camera,group,update,visible:false,x:0,y:0,tx:0,ty:0,w:0,h:0};
  canvas.addEventListener('pointermove',e=>{const r=canvas.getBoundingClientRect();view.tx=((e.clientX-r.left)/r.width-.5);view.ty=((e.clientY-r.top)/r.height-.5);if(paused)paint(view);});
  canvas.addEventListener('pointerleave',()=>{view.tx=view.ty=0;});return view;
});
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let paused=reduced,speed=1,light=false,time=2,last=0,lastPaint=0,renderWidth=0,renderHeight=0;
function size(view){const r=view.canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,1.7);view.w=Math.round(r.width);view.h=Math.round(r.height);view.canvas.width=Math.round(r.width*dpr);view.canvas.height=Math.round(r.height*dpr);view.camera.aspect=r.width/r.height;view.camera.updateProjectionMatrix();}
function paint(view){
  if(!view.w||!view.h)return;
  const {canvas,ctx}=view;view.x+=(view.tx-view.x)*.09;view.y+=(view.ty-view.y)*.09;
  view.camera.position.x=view.x*.65;view.camera.position.y=-view.y*.45;view.camera.lookAt(0,0,0);
  view.update(time);view.scene.background.set(light?0xdbdce1:0x111116);
  if(renderWidth!==view.w||renderHeight!==view.h){renderer.setSize(view.w,view.h,false);renderWidth=view.w;renderHeight=view.h;}
  renderer.render(view.scene,view.camera);
  ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(renderer.domElement,0,0,canvas.width,canvas.height);view.card.classList.add('ready');
}
views.forEach(size);
if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>entries.forEach(e=>{const view=views.find(v=>v.card===e.target);view.visible=e.isIntersecting;if(view.visible)paint(view);}),{rootMargin:'100px'});views.forEach(v=>observer.observe(v.card));}else{views.forEach(v=>v.visible=true);}
const pause=document.getElementById('pause');function updatePause(){pause.textContent=paused?'▶ Davom ettirish':'Ⅱ To‘xtatish';pause.setAttribute('aria-pressed',String(paused));}updatePause();
pause.addEventListener('click',()=>{paused=!paused;updatePause();});
document.getElementById('speed').addEventListener('click',e=>{speed=speed===1?.5:speed===.5?1.5:1;e.currentTarget.textContent=`Tezlik · ${speed}×`;});
document.getElementById('background').addEventListener('click',e=>{light=!light;document.body.classList.toggle('light-stage',light);e.currentTarget.textContent=light?'Fon · yorug‘':'Fon · qorong‘i';e.currentTarget.setAttribute('aria-pressed',String(light));views.forEach(v=>{if(v.visible)paint(v);});});
let resizing;addEventListener('resize',()=>{clearTimeout(resizing);resizing=setTimeout(()=>{views.forEach(size);views.forEach(v=>{if(v.visible)paint(v);});},100);});
const overview=document.getElementById('overview');
function updateOverview(){const compact=document.body.classList.contains('overview');overview.setAttribute('aria-pressed',String(compact));overview.textContent=compact?'Yirik ko‘rinish':'Barchasini solishtirish';}updateOverview();
overview.addEventListener('click',()=>{document.body.classList.toggle('overview');updateOverview();requestAnimationFrame(()=>{views.forEach(size);views.forEach(v=>{if(v.visible)paint(v);});});});
try {const choice=Number(localStorage.getItem('mg-liquid-choice'));if(choice>=1&&choice<=10)document.querySelectorAll('.pick')[choice-1].click();}catch{}
renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();fail('3D konteksti uzildi. Sahifani yangilang.');paused=true;updatePause();});
function loop(now){const dt=last?Math.min((now-last)/1000,.06):0;last=now;if(!paused&&!document.hidden)time+=dt*speed;if(!paused&&!document.hidden&&now-lastPaint>1000/30){lastPaint=now;views.forEach(v=>{if(v.visible)paint(v);});}requestAnimationFrame(loop);}requestAnimationFrame(loop);
views.forEach(v=>{const r=v.card.getBoundingClientRect();if(r.top<innerHeight+100&&r.bottom>0){v.visible=true;paint(v);}});
}catch(e){console.error(e);fail('3D sahnani yuklab bo‘lmadi. Sahifani yangilang; davom etsa brauzer konsolini tekshiring.');}
}
