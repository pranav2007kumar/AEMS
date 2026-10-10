import * as THREE from './vendor/three.module.js';


export async function mountCampus(container,hostel){
 const data=await fetch('./campus-data.json').then(r=>{if(!r.ok)throw new Error('Campus map unavailable');return r.json()});
 if(!container.isConnected)return {dispose(){},setStep(){}};
 const campusConfig={verified:true,geoReference:{...data.origin,x:0,z:0,bearingDegrees:0}};
 const scene=new THREE.Scene();scene.background=new THREE.Color('#e7edf0');scene.fog=new THREE.Fog('#e7edf0',500,1100);
 let renderer;
 try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});}catch{container.innerHTML='<div class="scene-fallback">3D rendering is unavailable in this browser. Enable hardware acceleration or try another browser. The directions remain available beside this view.</div>';return {dispose(){},setStep(){}};}
 renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;container.prepend(renderer.domElement);
 renderer.domElement.setAttribute('aria-label','Interactive 3D Coimbatore campus. Drag to rotate, scroll to zoom.');
 const camera=new THREE.PerspectiveCamera(40,1,.1,1800);
 scene.add(new THREE.HemisphereLight(0xffffff,0x738168,2.5));
 const sun=new THREE.DirectionalLight(0xfff3dd,4);sun.position.set(-180,300,100);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-270,right:270,top:270,bottom:-270,near:1,far:850});sun.shadow.bias=-.0005;sun.shadow.normalBias=.25;scene.add(sun);
 const materials=new Map();
 const mat=color=>{if(!materials.has(color))materials.set(color,new THREE.MeshStandardMaterial({color,roughness:.85}));return materials.get(color)};
 function mesh(geo,color,x,y,z){const o=new THREE.Mesh(geo,mat(color));o.position.set(x,y,z);o.castShadow=true;o.receiveShadow=true;scene.add(o);return o}
 const box=(w,h,d,c,x,y,z)=>mesh(new THREE.BoxGeometry(w,h,d),c,x,y,z);
 const cylinder=(r,h,c,x,y,z)=>mesh(new THREE.CylinderGeometry(r,r,h,24),c,x,y,z);

 const boundary=data.boundary;
 const minX=Math.min(...boundary.map(p=>p[0])),maxX=Math.max(...boundary.map(p=>p[0]));
 const minZ=Math.min(...boundary.map(p=>p[1])),maxZ=Math.max(...boundary.map(p=>p[1]));
 const centre=new THREE.Vector3((minX+maxX)/2,0,(minZ+maxZ)/2);
 function polygon(points,height,color,y=0){const shape=new THREE.Shape(points.map(p=>new THREE.Vector2(p[0],-p[1])));const geo=new THREE.ExtrudeGeometry(shape,{depth:height,bevelEnabled:false});geo.rotateX(-Math.PI/2);return mesh(geo,color,0,y,0)}
 box(maxX-minX+60,2,maxZ-minZ+60,'#c6d2bf',centre.x,-1.2,centre.z);polygon(boundary,.3,'#a6bc91',-.1);
 // Real OSM footprints, with illustrative heights and facade detail.
 const windowTransforms=[];
 for(const b of data.buildings){
  const selected=b.name===hostel;const height=Math.max(1.2,b.levels*1.7);
  polygon(b.points,height,selected?'#e7cab4':'#eee1cd',.4);polygon(b.points,.3,selected?'#a72f58':'#c2b499',height+.45);
  for(let i=1;i<b.points.length;i++){
   const a=b.points[i-1],c=b.points[i],len=Math.hypot(c[0]-a[0],c[1]-a[1]);if(len>65)continue;
   const dx=(c[0]-a[0])/len,dz=(c[1]-a[1])/len,angle=Math.atan2(dx,dz);
   for(let f=0;f<b.levels;f++)for(let j=1;j<len-1;j+=1.6){windowTransforms.push([a[0]+dx*j,.9+f*1.7+.5,a[1]+dz*j,angle])}
  }
  if(b.name){const c=b.points.reduce((a,p)=>[a[0]+p[0],a[1]+p[1]],[0,0]).map(v=>v/b.points.length);if(selected||/Academic Block|Library|School of Business|Canteen|Bhavanam/.test(b.name))label(b.name.replace(' - School of Engineering','').replace(' - International school of Law',''),c[0],height+5,c[1],selected?'#bb0750':'#344b4c',selected?28:23)}
 }
 const windows=new THREE.InstancedMesh(new THREE.BoxGeometry(.07,.9,.7),mat('#607e88'),windowTransforms.length);const temp=new THREE.Object3D();windowTransforms.forEach(([x,y,z,angle],i)=>{temp.position.set(x,y,z);temp.rotation.set(0,angle,0);temp.updateMatrix();windows.setMatrixAt(i,temp.matrix)});windows.receiveShadow=true;scene.add(windows);
 for(const area of data.areas)polygon(area.points,.06,area.kind==='swimming_pool'?'#65b3cf':area.kind==='pitch'?'#7aab70':'#96b485',.32);
 function segment(a,b,width,color,y){const d=new THREE.Vector3(b[0]-a[0],0,b[1]-a[1]);const m=box(width,.05,d.length(),color,(a[0]+b[0])/2,y,(a[1]+b[1])/2);m.rotation.y=Math.atan2(d.x,d.z);return m}
 for(const road of data.roads){const width=['footway','path','steps'].includes(road.kind)?.8:2.5;for(let i=1;i<road.points.length;i++){segment(road.points[i-1],road.points[i],width+.8,'#d6d9ce',.42);segment(road.points[i-1],road.points[i],width,'#606b70',.5)}}
 // Street trees are illustrative landscaping, not surveyed trees.
 const leaves=new THREE.IcosahedronGeometry(1.2,2),trunk=new THREE.CylinderGeometry(.12,.17,1.6,8);
 for(const road of data.roads){if(['footway','path','steps'].includes(road.kind))continue;for(let i=1;i<road.points.length;i++){const a=road.points[i-1],b=road.points[i],len=Math.hypot(b[0]-a[0],b[1]-a[1]);for(let t=5;t<len;t+=12){const x=a[0]+(b[0]-a[0])*t/len+3,z=a[1]+(b[1]-a[1])*t/len;mesh(trunk,'#89755b',x,1.2,z);mesh(leaves,'#6b935c',x,2.6,z)}}}
 for(const l of data.landmarks){cylinder(.8,.6,'#d5c4a3',l.point[0],.8,l.point[1]);if(/Statue|statue/.test(l.name))mesh(new THREE.ConeGeometry(.6,2,12),'#9b8561',l.point[0],2,l.point[1]);label(l.name,l.point[0],6,l.point[1],'#40565b',16)}
 // Main-gate coordinate comes directly from the public map.
 label('MAIN GATE',0,9,0,'#bb0750',24);[-3,3].forEach(x=>box(.5,4,.5,'#dec9ac',x,2,0));box(7,.6,.7,'#a32c51',0,4.1,0);
 const routeData=data.routes[hostel];
 let routeCoords=routeData?.points;
 if(!routeCoords||routeCoords.length<2){routeCoords=[[0,0],[0,-1]];container.querySelector('[data-gps-detail]').textContent='No mapped approach route for this destination.';}
 const allPoints=routeCoords.map(p=>new THREE.Vector3(p[0],.9,p[1]));
 const path=new THREE.CurvePath();for(let i=1;i<allPoints.length;i++)if(allPoints[i].distanceTo(allPoints[i-1])>.001)path.add(new THREE.LineCurve3(allPoints[i-1],allPoints[i]));
 const points=[0,.35,.75,1].map(t=>path.getPointAt(t));
 const route=mesh(new THREE.TubeGeometry(path,300,.33,10,false),'#ed1b6d',0,0,0);route.material=new THREE.MeshStandardMaterial({color:'#ed1b6d',emissive:'#bb0750',emissiveIntensity:.6});
 const marker=mesh(new THREE.TorusGeometry(1.6,.2,10,48),'#13ae9e',points[0].x,1.2,points[0].z);marker.rotation.x=Math.PI/2;
 const movingCar=new THREE.Group();scene.add(movingCar);const carBody=new THREE.Mesh(new THREE.BoxGeometry(.9,.55,1.9),mat('#bb0750'));carBody.position.y=.9;movingCar.add(carBody);const glass=new THREE.Mesh(new THREE.BoxGeometry(.8,.4,1),mat('#304f5a'));glass.position.y=1.3;movingCar.add(glass);movingCar.position.copy(points[0]);
 points.forEach((p,i)=>label(String(i+1),p.x,4,p.z,'#bb0750',3));
 label('HOSTEL APPROACH',points[3].x,5,points[3].z,'#bb0750',22);
 function label(text,x,y,z,color,width){
  const canvas=document.createElement('canvas');const c=canvas.getContext('2d');c.font='600 36px Arial';canvas.width=Math.ceil(c.measureText(text).width)+48;canvas.height=76;
  c.fillStyle='rgba(255,255,255,.96)';c.beginPath();c.roundRect(2,2,canvas.width-4,72,14);c.fill();c.fillStyle=color;c.font='600 36px Arial';c.textAlign='center';c.textBaseline='middle';c.fillText(text,canvas.width/2,40);
  const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;const m=new THREE.SpriteMaterial({map:texture,depthTest:false});const sprite=new THREE.Sprite(m);sprite.position.set(x,y,z);sprite.scale.set(width,width*canvas.height/canvas.width,1);sprite.renderOrder=10;scene.add(sprite);
 }
 let yaw=.2,pitch=1.08,distance=430,target=centre.clone(),targetGoal=target.clone(),disposed=false,tour=false,tourStart=0,frame;
 function stopTour(){tour=false;const b=container.querySelector('[data-3d="tour"]');if(b)b.textContent='Play route tour'}
 function setStep(index){stopTour();marker.position.copy(points[index]);marker.position.y=1.2;movingCar.position.set(points[index].x,.65,points[index].z);movingCar.rotation.y=index===2?(isLeft?Math.PI/2:-Math.PI/2):0;targetGoal.copy(points[index]);targetGoal.y=0;distance=Math.min(distance,110);}
 function resize(){const r=container.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix()}
 const observer=new ResizeObserver(resize);observer.observe(container);resize();
 const canvas=renderer.domElement;let drag=null;const pointers=new Map();let pinchDistance=0;
 canvas.style.touchAction='none';canvas.onpointerdown=e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,[e.clientX,e.clientY]);drag=[e.clientX,e.clientY];if(pointers.size===2){const [a,b]=[...pointers.values()];pinchDistance=Math.hypot(a[0]-b[0],a[1]-b[1])}};
 canvas.onpointermove=e=>{if(!pointers.has(e.pointerId))return;pointers.set(e.pointerId,[e.clientX,e.clientY]);if(pointers.size===2){const [a,b]=[...pointers.values()];const d=Math.hypot(a[0]-b[0],a[1]-b[1]);distance=THREE.MathUtils.clamp(distance*pinchDistance/d,45,550);pinchDistance=d;return}if(drag){yaw-=(e.clientX-drag[0])*.007;pitch=THREE.MathUtils.clamp(pitch+(e.clientY-drag[1])*.005,.28,1.47);drag=[e.clientX,e.clientY]}};
 canvas.onpointerup=canvas.onpointercancel=e=>{pointers.delete(e.pointerId);drag=null};canvas.onwheel=e=>{e.preventDefault();distance=THREE.MathUtils.clamp(distance+e.deltaY*.09,45,550)};canvas.addEventListener('wheel',canvas.onwheel,{passive:false});
 const listen=(selector,fn)=>{const el=container.querySelector(selector);if(el)el.onclick=fn};
 listen('[data-3d="reset"]',()=>{stopTour();yaw=.2;pitch=1.08;distance=430;targetGoal.copy(centre)});
 listen('[data-3d="top"]',()=>{stopTour();pitch=1.47;yaw=0;distance=380;targetGoal.copy(centre)});
 listen('[data-3d="in"]',()=>distance=Math.max(45,distance-15));listen('[data-3d="out"]',()=>distance=Math.min(550,distance+15));
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
 function stopGps(){if(gpsWatch!==null)navigator.geolocation.clearWatch(gpsWatch);gpsWatch=null;gpsFollow=false;gpsDot.visible=false;accuracyCircle.visible=false;gpsPoint=null;if(gpsButton)gpsButton.textContent='Enable GPS';if(followButton){followButton.disabled=true;followButton.textContent='Follow GPS';followButton.setAttribute('aria-pressed','false')}}
 function gpsError(error){stopGps();gpsStatus.textContent=error.code===1?'Location permission denied':error.code===2?'GPS position unavailable':'GPS timed out';gpsDetail.textContent='You can still explore the 3D model and use the sample directions.';}
 listen('[data-3d="gps"]',()=>{
  if(gpsWatch!==null){stopGps();gpsStatus.textContent='GPS off';gpsDetail.textContent='Your location is read only when you enable GPS.';return}
  if(!navigator.geolocation){gpsStatus.textContent='GPS is not supported by this browser';return}
  gpsStatus.textContent='Waiting for location permission…';gpsDetail.textContent='Allow location in your browser to see your live GPS accuracy.';gpsButton.textContent='Stop GPS';
  gpsWatch=navigator.geolocation.watchPosition(position=>{
   const {latitude,longitude,accuracy}=position.coords;gpsAccuracy=accuracy;gpsStatus.textContent=`GPS active · ±${Math.round(accuracy)} m`;
   if(!validGeo){gpsDetail.textContent=`${latitude.toFixed(5)}, ${longitude.toFixed(5)} · Sample map is not georeferenced; position and camera follow are unavailable.`;return}
   const ref=campusConfig.geoReference;const north=(latitude-ref.latitude)*111320;const east=(longitude-ref.longitude)*111320*Math.cos(ref.latitude*Math.PI/180);const angle=ref.bearingDegrees*Math.PI/180;
   const x=(ref.x+east*Math.cos(angle)-north*Math.sin(angle))*data.metresToWorld,z=(ref.z-east*Math.sin(angle)-north*Math.cos(angle))*data.metresToWorld;
   let inside=false;for(let i=0,j=boundary.length-1;i<boundary.length;j=i++){const [a,b]=boundary[i],[c,d]=boundary[j];if((b>z)!==(d>z)&&x<(c-a)*(z-b)/(d-b)+a)inside=!inside;}
   if(!inside){gpsDetail.textContent='Your location is outside the mapped campus area.';gpsPoint=null;gpsDot.visible=false;accuracyCircle.visible=false;followButton.disabled=true;gpsFollow=false;return}
   gpsPoint=new THREE.Vector3(x,0,z);gpsDot.position.set(x,2,z);gpsDot.visible=true;accuracyCircle.position.set(x,.6,z);accuracyCircle.scale.setScalar(accuracy*data.metresToWorld);accuracyCircle.visible=true;followButton.disabled=false;gpsDetail.textContent=`Public-map position · updated ${new Date(position.timestamp).toLocaleTimeString()}`;
   if(gpsFollow)targetGoal.copy(gpsPoint);
  },gpsError,{enableHighAccuracy:true,timeout:20000,maximumAge:3000});
 });
 listen('[data-3d="follow"]',()=>{if(!gpsPoint)return;gpsFollow=!gpsFollow;stopTour();followButton.textContent=gpsFollow?'Following GPS':'Follow GPS';followButton.setAttribute('aria-pressed',String(gpsFollow));if(gpsFollow){targetGoal.copy(gpsPoint);distance=70}});
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 function animate(time){if(disposed)return;frame=requestAnimationFrame(animate);target.lerp(targetGoal,.06);
  if(tour){const t=Math.max(0,(time-tourStart)/18000)%1;const pos=path.getPointAt(t);const tangent=path.getPointAt(Math.min(1,t+.001)).sub(path.getPointAt(Math.max(0,t-.001))).normalize();movingCar.position.set(pos.x,.65,pos.z);movingCar.rotation.y=Math.atan2(-tangent.x,-tangent.z);marker.position.set(pos.x,1.2,pos.z);}
  if(!reduced)marker.scale.setScalar(1+Math.sin(time*.003)*.07);
  camera.position.set(target.x+distance*Math.sin(yaw)*Math.cos(pitch),target.y+distance*Math.sin(pitch),target.z+distance*Math.cos(yaw)*Math.cos(pitch));camera.lookAt(target);renderer.render(scene,camera);
 }
 frame=requestAnimationFrame(animate);
 return {setStep,dispose(){stopGps();disposed=true;cancelAnimationFrame(frame);observer.disconnect();const geos=new Set(),mats=new Set(),textures=new Set();scene.traverse(o=>{if(o.geometry)geos.add(o.geometry);if(o.material){for(const m of Array.isArray(o.material)?o.material:[o.material]){mats.add(m);if(m.map)textures.add(m.map)}}});geos.forEach(g=>g.dispose());mats.forEach(m=>m.dispose());textures.forEach(t=>t.dispose());renderer.dispose();canvas.remove()}};
}
