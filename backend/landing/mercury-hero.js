// The selected Mercury concept, isolated from the ten-scene exploration gallery.
const canvas=document.getElementById('mercury'),stage=document.getElementById('mercury-stage'),button=document.getElementById('motion-toggle');
const media=matchMedia('(prefers-reduced-motion: reduce)');
let paused=media.matches,visible=true,time=2,last=0,lastPaint=0,x=0,y=0,tx=0,ty=0,renderer,render=()=>{};
try{if(localStorage.getItem('mg-motion')==='paused')paused=true;}catch{}
function syncButton(){button.setAttribute('aria-pressed',String(paused));button.setAttribute('aria-label',paused?'3D animatsiyani davom ettirish':'3D animatsiyani to‘xtatish');button.innerHTML=`${paused?'▶':'Ⅱ'} <span>${paused?'Davom ettirish':'Harakat'}</span>`;stage.classList.toggle('motion-paused',paused);}
syncButton();
button.addEventListener('click',()=>{paused=!paused;syncButton();try{localStorage.setItem('mg-motion',paused?'paused':'playing');}catch{}render();});
media.addEventListener('change',e=>{paused=e.matches;syncButton();render();});
if('IntersectionObserver' in window)new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)render();},{rootMargin:'80px'}).observe(stage);
try{
  const [THREE,{RoomEnvironment}]=await Promise.all([import('./vendor/three.module.js'),import('./vendor/RoomEnvironment.js')]);
  renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,innerWidth<680?1.5:1.7));renderer.setClearColor(0x000000,0);
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.45;
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(35,1,.1,30);camera.position.z=5.3;
  const generator=new THREE.PMREMGenerator(renderer),room=new RoomEnvironment();
  const environment=generator.fromScene(room,.04);scene.environment=environment.texture;room.dispose();generator.dispose();
  const geometry=new THREE.SphereGeometry(1,innerWidth<680?48:64,innerWidth<680?32:40),attribute=geometry.attributes.position,base=attribute.array.slice();
  const material=new THREE.MeshPhysicalMaterial({color:0xe2e3eb,metalness:1,roughness:.17,clearcoat:1,clearcoatRoughness:.1,envMapIntensity:1.15});
  const body=new THREE.Mesh(geometry,material);scene.add(body);
  const key=new THREE.DirectionalLight(0xffffff,3);key.position.set(-3,4,5);scene.add(key);
  const rim=new THREE.PointLight(0xcad8ff,22,10);rim.position.set(3,1,-1);scene.add(rim);
  const accent=new THREE.PointLight(0xd6ff85,7,10);accent.position.set(-3,-1,1);scene.add(accent);
  let lost=false;
  render=()=>{
    if(lost||!visible)return;
    x+=(tx-x)*.08;y+=(ty-y)*.08;
    for(let i=0;i<attribute.count;i++){
      const a=base[i*3],b=base[i*3+1],c=base[i*3+2];
      const r=1+.13*Math.sin(3*a+time*.9)*Math.cos(3*b-time*.6)+.09*Math.sin(4*c+time*.5)+.05*Math.sin(b*6+a*2-time);
      attribute.setXYZ(i,a*r,b*r,c*r);
    }
    attribute.needsUpdate=true;geometry.computeVertexNormals();
    body.rotation.set(time*.12+y*.25,time*.2+x*.35,Math.sin(time*.4)*.12);
    camera.position.x=x*.45;camera.position.y=-y*.3;camera.lookAt(0,0,0);renderer.render(scene,camera);
    stage.classList.add('webgl-ready');
  };
  const resize=()=>{const r=stage.getBoundingClientRect();if(!r.width||!r.height)return;renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();render();};
  if('ResizeObserver'in window)new ResizeObserver(resize).observe(stage);else addEventListener('resize',resize);
  stage.addEventListener('pointermove',e=>{const r=stage.getBoundingClientRect();tx=(e.clientX-r.left)/r.width-.5;ty=(e.clientY-r.top)/r.height-.5;if(paused)render();},{passive:true});
  stage.addEventListener('pointerleave',()=>{tx=ty=0;if(paused){x=y=0;render();}});
  document.addEventListener('mg:theme',render);
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();lost=true;stage.classList.remove('webgl-ready');button.disabled=true;button.title='3D qayta yuklanishi uchun sahifani yangilang';});
  addEventListener('pagehide',e=>{if(!e.persisted){lost=true;geometry.dispose();material.dispose();environment.dispose();renderer.dispose();}});
  resize();
  function frame(now){const dt=last?Math.min((now-last)/1000,.06):0;last=now;if(!paused&&visible&&!document.hidden&&!lost){time+=dt;if(now-lastPaint>=1000/30){lastPaint=now;render();}}requestAnimationFrame(frame);}requestAnimationFrame(frame);
}catch(error){
  // CSS Mercury remains visible; the page and every navigation/form control still work.
  renderer?.dispose();stage.classList.remove('webgl-ready');button.hidden=true;
  console.info('MarosimGo: statik vizual ishlatilmoqda.',error.message);
}
