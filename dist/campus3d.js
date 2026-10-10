import * as THREE from './vendor/three.module.js';
import {campusConfig} from './campus-config.js';

export function mountCampus(container,hostel,onStep){
 const scene=new THREE.Scene();scene.background=new THREE.Color('#e7edf0');scene.fog=new THREE.Fog('#e7edf0',170,360);
 let renderer;
 try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});}catch{container.innerHTML='<div class="scene-fallback">3D rendering is unavailable in this browser. Enable hardware acceleration or try another browser. The directions remain available beside this view.</div>';return {dispose(){},setStep(){}};}
 renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;container.prepend(renderer.domElement);
 renderer.domElement.setAttribute('aria-label','Interactive 3D sample campus. Drag to rotate, scroll to zoom.');
 const camera=new THREE.PerspectiveCamera(40,1,.1,600);
 scene.add(new THREE.HemisphereLight(0xffffff,0x738168,2.5));
 const sun=new THREE.DirectionalLight(0xfff3dd,4);sun.position.set(-65,100,55);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-100,right:100,top:100,bottom:-100,near:1,far:260});sun.shadow.bias=-.0005;sun.shadow.normalBias=.25;scene.add(sun);
 const materials=new Map();
 const mat=color=>{if(!materials.has(color))materials.set(color,new THREE.MeshStandardMaterial({color,roughness:.85}));return materials.get(color)};
 function mesh(geo,color,x,y,z){const o=new THREE.Mesh(geo,mat(color));o.position.set(x,y,z);o.castShadow=true;o.receiveShadow=true;scene.add(o);return o}
 const box=(w,h,d,c,x,y,z)=>mesh(new THREE.BoxGeometry(w,h,d),c,x,y,z);
 const cylinder=(r,h,c,x,y,z)=>mesh(new THREE.CylinderGeometry(r,r,h,24),c,x,y,z);
 box(174,3,151,'#d1d9cc',0,-1.6,0);box(170,.3,147,'#91ad80',0,.02,0);
 // Roads, sidewalks, and lane markings.
 function road(w,d,x,z){box(w+4,.35,d+4,'#dce0d8',x,.2,z);box(w,.08,d,'#555f66',x,.42,z)}
 road(12,116,0,10);road(125,12,0,-12);road(10,35,-48,-32);road(10,35,48,-32);
 road(170,10,0,66);
 for(let z=-40;z<65;z+=9)box(.35,.05,4,'#e4d7a5',0,.49,z);
 for(let x=-58;x<=58;x+=9)box(4,.05,.3,'#e4d7a5',x,.49,-12);
 for(let x=-6;x<7;x+=2)box(1,.05,4,'#f2f1e9',x,.5,53);
 // Building model: stone plinth, facade, floor bands, balconies, windows, roof and reception canopy.
 function building(x,z,w,d,h,color,name,selected=false){
  box(w+3,.7,d+3,'#d6d3c7',x,.6,z);box(w,h,d,color,x,h/2+.9,z);
  box(w+1,1,d+1,selected?'#8f234b':'#b2a38b',x,h+1,z);
  box(w-2,.5,d-2,'#d1c6b0',x,h+1.8,z);
  for(let floor=0;floor<Math.floor(h/4);floor++){
   const y=3+floor*4;
   box(w+.4,.3,d+.4,'#ede5d5',x,y-1.5,z);
   for(let a=-w/2+2;a<w/2-1;a+=3.4){
    box(1.5,2,.14,'#425b65',x+a,y,z+d/2+.1);box(1.5,2,.14,'#425b65',x+a,y,z-d/2-.1);
    box(.09,2,.18,'#ded9cc',x+a,y,z+d/2+.22);
   }
   for(let a=-d/2+2;a<d/2-1;a+=3.5){box(.14,2,1.5,'#4b6670',x+w/2+.1,y,z+a);box(.14,2,1.5,'#4b6670',x-w/2-.1,y,z+a)}
  }
  box(6,3,.3,'#304851',x,2.3,z+d/2+.15);box(10,.45,5,'#ede0c8',x,4.6,z+d/2+2);
  [-4,4].forEach(a=>box(.4,3.8,.4,'#dfd5bf',x+a,2.4,z+d/2+3.7));
  box(7,.35,4,'#c2b6a1',x,.7,z+d/2+3);
  for(let a=-w/2+3;a<w/2;a+=8)box(3,.9,2,'#a6aaa5',x+a,h+2.2,z);
  label(name,x,h+7,z,selected?'#bb0750':'#273d41',selected?22:20);
 }
 const isLeft=hostel==='Anugraha';
 building(-48,-53,29,21,18,'#eadac0','ANUGRAHA',isLeft);
 building(48,-53,29,21,18,'#e8d9c5','AMRITAMAYI',!isLeft);
 building(-42,23,37,24,14,'#e6d4ba','ACADEMIC BLOCK');
 building(42,23,25,20,8,'#dfcfb5','VISITOR SERVICES');
 building(-65,-6,17,18,8,'#e8d6bd','LIBRARY');
 // Gatehouse and entrance arch.
 box(11,5,8,'#e2cfb0',15,2.9,56);box(12,.6,9,'#8f234b',15,5.8,56);
 box(5,2,.12,'#425b65',15,3.4,60.1);
 [-10,10].forEach(x=>box(1.5,8,1.5,'#dcc8a8',x,4,53));box(22,2,2,'#96294d',0,8,53);
 label('MAIN GATE',0,13,57,'#273d41',21);
 // Gardens, courtyard fountain, lawns and tree-lined avenue.
 cylinder(9,.45,'#dad4c6',-28,.5,-23);cylinder(6,.6,'#b8c8c6',-28,.9,-23);cylinder(5,.2,'#71b3c7',-28,1.3,-23);cylinder(1.5,2,'#cec8b7',-28,2,-23);
 for(let i=0;i<8;i++){const a=i*Math.PI/4;box(3,.6,1,'#c4bba8',-28+Math.cos(a)*8,1,-23+Math.sin(a)*8)}
 function tree(x,z,scale=1){
  cylinder(.45*scale,4*scale,'#81664a',x,2*scale,z);
  const crown=mesh(new THREE.IcosahedronGeometry(2.6*scale,2),'#527b4a',x,5*scale,z);crown.scale.y=1.25;
  mesh(new THREE.IcosahedronGeometry(2.1*scale,1),'#719453',x+.8*scale,6.4*scale,z);
 }
 for(let z=-35;z<=44;z+=10){tree(-10,z,.85);tree(10,z,.85)}
 for(let x=-75;x<=75;x+=10){tree(x,-68,1);if(Math.abs(x)>25)tree(x,55,.95)}
 for(let z=-52;z<48;z+=12){tree(-78,z);tree(78,z)}
 [[-25,42],[-64,43],[26,42],[63,43],[-21,-45],[22,-44],[65,-29],[-65,-29]].forEach(([x,z])=>tree(x,z,1.15));
 for(let z=-35;z<45;z+=16){cylinder(.13,6,'#626b67',-8,3,z);box(1,.3,2,'#eee8cf',-8,6,z)}
 // Parking bays and parked cars.
 box(22,.08,12,'#606a70',55,.45,46);
 for(let x=46;x<66;x+=4)box(.12,.04,10,'#d9dedb',x,.51,46);
 function car(x,z,color){const g=new THREE.Group();scene.add(g);g.position.set(x,.65,z);
  function part(w,h,d,c,px,py,pz){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat(c));m.position.set(px,py,pz);m.castShadow=true;g.add(m)}
  part(2,1,4.1,color,0,.8,0);part(1.8,.9,2.1,'#354b57',0,1.6,-.2);part(1.9,.15,2.1,color,0,2.1,-.2);
  for(const a of [-1,1])for(const b of [-1.3,1.3]){const wheel=new THREE.Mesh(new THREE.CylinderGeometry(.45,.45,.24,16),mat('#273039'));wheel.rotation.z=Math.PI/2;wheel.position.set(a,.45,b);g.add(wheel)}
  part(1.4,.18,.1,'#fff2d1',0,.9,-2.1);return g;
 }
 car(48,46,'#ecede8');car(56,46,'#58717c');car(64,46,'#b76f55');
 const movingCar=car(2,48,'#bb0750');
 const branch=isLeft?-48:48;
 const points=[new THREE.Vector3(2,1,48),new THREE.Vector3(2,1,-12),new THREE.Vector3(branch,1,-12),new THREE.Vector3(branch,1,-39)];
 const path=new THREE.CurvePath();for(let i=1;i<points.length;i++)path.add(new THREE.LineCurve3(points[i-1],points[i]));
 const route=mesh(new THREE.TubeGeometry(path,150,.45,10,false),'#e51968',0,0,0);route.material=new THREE.MeshStandardMaterial({color:'#ed1b6d',emissive:'#bb0750',emissiveIntensity:.6,roughness:.45});
 const marker=mesh(new THREE.TorusGeometry(2.4,.35,12,48),'#13ae9e',2,1.2,48);marker.rotation.x=Math.PI/2;
 points.forEach((p,i)=>{cylinder(.9,.35,'#fff4ed',p.x,1.1,p.z);label(String(i+1),p.x,4,p.z,'#bb0750',5)});
 label('HOSTEL RECEPTION',branch,7,-39,'#bb0750',21);
 function label(text,x,y,z,color,width){
  const canvas=document.createElement('canvas');const c=canvas.getContext('2d');c.font='600 36px Arial';canvas.width=Math.ceil(c.measureText(text).width)+48;canvas.height=76;
  c.fillStyle='rgba(255,255,255,.96)';c.beginPath();c.roundRect(2,2,canvas.width-4,72,14);c.fill();c.fillStyle=color;c.font='600 36px Arial';c.textAlign='center';c.textBaseline='middle';c.fillText(text,canvas.width/2,40);
  const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;const m=new THREE.SpriteMaterial({map:texture,depthTest:false});const sprite=new THREE.Sprite(m);sprite.position.set(x,y,z);sprite.scale.set(width,width*canvas.height/canvas.width,1);sprite.renderOrder=10;scene.add(sprite);
 }
 let yaw=.57,pitch=.83,distance=160,target=new THREE.Vector3(0,0,-3),targetGoal=target.clone(),disposed=false,tour=false,tourStart=0,frame;
 function stopTour(){tour=false;const b=container.querySelector('[data-3d="tour"]');if(b)b.textContent='Play route tour'}
 function setStep(index){stopTour();marker.position.copy(points[index]);marker.position.y=1.2;movingCar.position.set(points[index].x,.65,points[index].z);movingCar.rotation.y=index===2?(isLeft?Math.PI/2:-Math.PI/2):0;targetGoal.copy(points[index]);targetGoal.y=0;distance=Math.min(distance,100);}
 function resize(){const r=container.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix()}
 const observer=new ResizeObserver(resize);observer.observe(container);resize();
 const canvas=renderer.domElement;let drag=null;const pointers=new Map();let pinchDistance=0;
 canvas.style.touchAction='none';canvas.onpointerdown=e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,[e.clientX,e.clientY]);drag=[e.clientX,e.clientY];if(pointers.size===2){const [a,b]=[...pointers.values()];pinchDistance=Math.hypot(a[0]-b[0],a[1]-b[1])}};
 canvas.onpointermove=e=>{if(!pointers.has(e.pointerId))return;pointers.set(e.pointerId,[e.clientX,e.clientY]);if(pointers.size===2){const [a,b]=[...pointers.values()];const d=Math.hypot(a[0]-b[0],a[1]-b[1]);distance=THREE.MathUtils.clamp(distance*pinchDistance/d,45,230);pinchDistance=d;return}if(drag){yaw-=(e.clientX-drag[0])*.007;pitch=THREE.MathUtils.clamp(pitch+(e.clientY-drag[1])*.005,.28,1.47);drag=[e.clientX,e.clientY]}};
 canvas.onpointerup=canvas.onpointercancel=e=>{pointers.delete(e.pointerId);drag=null};canvas.onwheel=e=>{e.preventDefault();distance=THREE.MathUtils.clamp(distance+e.deltaY*.09,45,230)};canvas.addEventListener('wheel',canvas.onwheel,{passive:false});
 const listen=(selector,fn)=>{const el=container.querySelector(selector);if(el)el.onclick=fn};
 listen('[data-3d="reset"]',()=>{stopTour();yaw=.57;pitch=.83;distance=160;targetGoal.set(0,0,-3)});
 listen('[data-3d="top"]',()=>{stopTour();pitch=1.47;yaw=0;distance=165;targetGoal.set(0,0,-3)});
 listen('[data-3d="in"]',()=>distance=Math.max(45,distance-15));listen('[data-3d="out"]',()=>distance=Math.min(230,distance+15));
 listen('[data-3d="tour"]',()=>{tour=!tour;tourStart=performance.now();container.querySelector('[data-3d="tour"]').textContent=tour?'Pause tour':'Play route tour'});
 listen('[data-3d="full"]',()=>{if(document.fullscreenElement)document.exitFullscreen();else container.requestFullscreen?.().catch(()=>{})});
 // GPS stays entirely on this device. Sample buildings are never treated as georeferenced.
 let gpsWatch=null,gpsPoint=null,gpsFollow=false,gpsAccuracy=null;
 const gpsDot=mesh(new THREE.SphereGeometry(1,24,16),'#278cff',0,2,0);gpsDot.visible=false;
 const accuracyMaterial=new THREE.MeshBasicMaterial({color:'#278cff',transparent:true,opacity:.13,depthWrite:false});
 const accuracyCircle=new THREE.Mesh(new THREE.CircleGeometry(1,64),accuracyMaterial);accuracyCircle.rotation.x=-Math.PI/2;accuracyCircle.position.y=.6;accuracyCircle.visible=false;scene.add(accuracyCircle);
 const gpsStatus=container.querySelector('[data-gps-status]');
 const gpsDetail=container.querySelector('[data-gps-detail]');
 const gpsButton=container.querySelector('[data-3d="gps"]');
 const followButton=container.querySelector('[data-3d="follow"]');
 const validGeo=campusConfig.verified&&campusConfig.geoReference;
 function stopGps(){if(gpsWatch!==null)navigator.geolocation.clearWatch(gpsWatch);gpsWatch=null;gpsFollow=false;gpsDot.visible=false;accuracyCircle.visible=false;gpsPoint=null;if(gpsButton)gpsButton.textContent='Enable GPS';if(followButton)followButton.disabled=true;}
 function gpsError(error){stopGps();gpsStatus.textContent=error.code===1?'Location permission denied':error.code===2?'GPS position unavailable':'GPS timed out';gpsDetail.textContent='You can still explore the 3D model and use the sample directions.';}
 listen('[data-3d="gps"]',()=>{
  if(gpsWatch!==null){stopGps();gpsStatus.textContent='GPS off';gpsDetail.textContent='Your location is read only when you enable GPS.';return}
  if(!navigator.geolocation){gpsStatus.textContent='GPS is not supported by this browser';return}
  gpsStatus.textContent='Waiting for location permission…';gpsDetail.textContent='Allow location in your browser to see your live GPS accuracy.';gpsButton.textContent='Stop GPS';
  gpsWatch=navigator.geolocation.watchPosition(position=>{
   const {latitude,longitude,accuracy}=position.coords;gpsAccuracy=accuracy;gpsStatus.textContent=`GPS active · ±${Math.round(accuracy)} m`;
   if(!validGeo){gpsDetail.textContent=`${latitude.toFixed(5)}, ${longitude.toFixed(5)} · Sample map is not georeferenced; position and camera follow are unavailable.`;return}
   const ref=campusConfig.geoReference;const north=(latitude-ref.latitude)*111320;const east=(longitude-ref.longitude)*111320*Math.cos(ref.latitude*Math.PI/180);const angle=ref.bearingDegrees*Math.PI/180;
   const x=ref.x+east*Math.cos(angle)-north*Math.sin(angle),z=ref.z-east*Math.sin(angle)-north*Math.cos(angle);
   if(Math.abs(x)>85||Math.abs(z)>73){gpsDetail.textContent='Your location is outside the mapped campus area.';gpsPoint=null;gpsDot.visible=false;accuracyCircle.visible=false;followButton.disabled=true;gpsFollow=false;return}
   gpsPoint=new THREE.Vector3(x,0,z);gpsDot.position.set(x,2,z);gpsDot.visible=true;accuracyCircle.position.set(x,.6,z);accuracyCircle.scale.setScalar(Math.min(accuracy,100));accuracyCircle.visible=true;followButton.disabled=false;gpsDetail.textContent=`Live campus position · updated ${new Date(position.timestamp).toLocaleTimeString()}`;
   if(gpsFollow)targetGoal.copy(gpsPoint);
  },gpsError,{enableHighAccuracy:true,timeout:20000,maximumAge:3000});
 });
 listen('[data-3d="follow"]',()=>{if(!gpsPoint)return;gpsFollow=!gpsFollow;stopTour();followButton.textContent=gpsFollow?'Following GPS':'Follow GPS';followButton.setAttribute('aria-pressed',String(gpsFollow));if(gpsFollow){targetGoal.copy(gpsPoint);distance=70}});
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 function animate(time){if(disposed)return;frame=requestAnimationFrame(animate);target.lerp(targetGoal,.06);
  if(tour){const t=((time-tourStart)/18000)%1;const pos=path.getPointAt(t);const tangent=path.getTangentAt(t);movingCar.position.set(pos.x,.65,pos.z);movingCar.rotation.y=Math.atan2(-tangent.x,-tangent.z);marker.position.set(pos.x,1.2,pos.z);}
  if(!reduced)marker.scale.setScalar(1+Math.sin(time*.003)*.07);
  camera.position.set(target.x+distance*Math.sin(yaw)*Math.cos(pitch),target.y+distance*Math.sin(pitch),target.z+distance*Math.cos(yaw)*Math.cos(pitch));camera.lookAt(target);renderer.render(scene,camera);
 }
 frame=requestAnimationFrame(animate);
 return {setStep,dispose(){stopGps();disposed=true;cancelAnimationFrame(frame);observer.disconnect();const geos=new Set(),mats=new Set(),textures=new Set();scene.traverse(o=>{if(o.geometry)geos.add(o.geometry);if(o.material){for(const m of Array.isArray(o.material)?o.material:[o.material]){mats.add(m);if(m.map)textures.add(m.map)}}});geos.forEach(g=>g.dispose());mats.forEach(m=>m.dispose());textures.forEach(t=>t.dispose());renderer.dispose();canvas.remove()}};
}
