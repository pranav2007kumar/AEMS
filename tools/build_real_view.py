from pathlib import Path
p=Path(__file__).resolve().parents[1]/'dist'
s=(p/'campus3d.js').read_text(encoding='utf-8')
s=s.replace("import {campusConfig} from './campus-config.js';",'')
s=s.replace('export function mountCampus(container,hostel,onStep){',"export async function mountCampus(container,hostel){\n const data=await fetch('./campus-data.json').then(r=>{if(!r.ok)throw new Error('Campus map unavailable');return r.json()});\n if(!container.isConnected)return {dispose(){},setStep(){}};\n const campusConfig={verified:true,geoReference:{...data.origin,x:0,z:0,bearingDegrees:0}};")
s=s.replace("new THREE.Fog('#e7edf0',170,360)","new THREE.Fog('#e7edf0',500,1100)")
s=s.replace('new THREE.PerspectiveCamera(40,1,.1,600)','new THREE.PerspectiveCamera(40,1,.1,1800)')
s=s.replace('sun.position.set(-65,100,55)','sun.position.set(-180,300,100)')
s=s.replace('left:-100,right:100,top:100,bottom:-100,near:1,far:260','left:-270,right:270,top:270,bottom:-270,near:1,far:850')
start=s.index(" box(174,3,151")
end=s.index(' let yaw=',start)
label=s[s.index(' function label(text,',start):end]
geometry=r'''
 const boundary=data.boundary;
 const minX=Math.min(...boundary.map(p=>p[0])),maxX=Math.max(...boundary.map(p=>p[0]));
 const minZ=Math.min(...boundary.map(p=>p[1])),maxZ=Math.max(...boundary.map(p=>p[1]));
 const centre=new THREE.Vector3((minX+maxX)/2,0,(minZ+maxZ)/2);
 function polygon(points,height,color,y=0){const shape=new THREE.Shape(points.map(p=>new THREE.Vector2(p[0],-p[1])));const geo=new THREE.ExtrudeGeometry(shape,{depth:height,bevelEnabled:false});geo.rotateX(-Math.PI/2);return mesh(geo,color,0,y,0)}
 box(maxX-minX+60,2,maxZ-minZ+60,'#c6d2bf',centre.x,-1.2,centre.z);polygon(boundary,.3,'#a6bc91',-.1);
 // Real OSM footprints, with illustrative heights and facade detail.
 for(const b of data.buildings){
  const selected=b.name===hostel;const height=Math.max(1.2,b.levels*1.7);
  polygon(b.points,height,selected?'#e7cab4':'#eee1cd',.4);polygon(b.points,.3,selected?'#a72f58':'#c2b499',height+.45);
  for(let i=1;i<b.points.length;i++){
   const a=b.points[i-1],c=b.points[i],len=Math.hypot(c[0]-a[0],c[1]-a[1]);if(len>65)continue;
   const dx=(c[0]-a[0])/len,dz=(c[1]-a[1])/len,angle=Math.atan2(dx,dz);
   for(let f=0;f<b.levels;f++)for(let j=1;j<len-1;j+=1.6){const window=box(.07,.9,.7,'#607e88',a[0]+dx*j,.9+f*1.7+.5,a[1]+dz*j);window.rotation.y=angle}
  }
  if(b.name){const c=b.points.reduce((a,p)=>[a[0]+p[0],a[1]+p[1]],[0,0]).map(v=>v/b.points.length);if(selected||/Academic Block|Library|School of Business|Canteen|Bhavanam/.test(b.name))label(b.name.replace(' - School of Engineering','').replace(' - International school of Law',''),c[0],height+5,c[1],selected?'#bb0750':'#344b4c',selected?28:23)}
 }
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
'''
s=s[:start]+geometry+label+s[end:]
s=s.replace('distance=160,target=new THREE.Vector3(0,0,-3)','distance=360,target=centre.clone()')
s=s.replace('distance=Math.min(distance,100)','distance=Math.min(distance,110)')
s=s.replace('45,230','45,550').replace('distance=160;targetGoal.set(0,0,-3)','distance=360;targetGoal.copy(centre)').replace('distance=165;targetGoal.set(0,0,-3)','distance=380;targetGoal.copy(centre)').replace('Math.min(230,distance+15)','Math.min(550,distance+15)')
s=s.replace('const x=ref.x+east*Math.cos(angle)-north*Math.sin(angle),z=ref.z-east*Math.sin(angle)-north*Math.cos(angle);','const x=(ref.x+east*Math.cos(angle)-north*Math.sin(angle))*data.metresToWorld,z=(ref.z-east*Math.sin(angle)-north*Math.cos(angle))*data.metresToWorld;')
s=s.replace('if(Math.abs(x)>85||Math.abs(z)>73)','if(x<minX||x>maxX||z<minZ||z>maxZ)')
s=s.replace('Math.min(accuracy,100)','Math.min(accuracy*data.metresToWorld,100)')
s=s.replace('Live campus position Â· updated','Public-map position Â· updated')
s=s.replace('Interactive 3D sample campus','Interactive 3D Coimbatore campus')
(p/'campus-real.js').write_text(s,encoding='utf-8')
