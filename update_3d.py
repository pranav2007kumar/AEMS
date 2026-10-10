from pathlib import Path
p=Path('D:/Hackathons/Genesis/amrita-entry/dist/app.js')
s=p.read_text(encoding='utf-8')
s=s.replace("let viewFilter='all'", "let campusView=null,campusMountVersion=0;\nlet viewFilter='all'")
start=s.index('<div class="section-label" style="margin-top:0"><h2>Gate → hostel reception')
end=s.index('</section><aside class="panel"><h2>Follow the route',start)
s=s[:start]+'''<div class="section-label" style="margin-top:0"><h2>Explore your route in 3D</h2><span>Interactive campus preview</span></div><div id="campus-3d" class="campus-scene"><div class="scene-loading" id="scene-loading">Preparing your 3D campus…</div><div class="scene-badge">3D CAMPUS <span>Sample layout</span></div><div class="scene-toolbar"><button type="button" data-3d="reset" title="Reset camera">Reset view</button><button type="button" data-3d="top">Top view</button><button type="button" data-3d="tour">Play route tour</button><button type="button" data-3d="in" aria-label="Zoom in">+</button><button type="button" data-3d="out" aria-label="Zoom out">−</button><button type="button" data-3d="full">Fullscreen</button></div><div class="scene-help">Drag to rotate · Scroll or pinch to zoom</div></div><div class="map-legend"><span><i class="route-line"></i>Route to ${esc(v.hostel)}</span><span><i class="route-ring"></i>Selected step / tour position</span></div><p class="hint">Explore the buildings in 3D or play the route tour. This is a demonstration, not live location tracking.</p>'''+s[end:]
s=s.replace("const marker=document.querySelector('#route-position');marker.setAttribute('cx',points[index][0]);marker.setAttribute('cy',points[index][1]);", "campusView?.setStep(index);")
target="document.querySelector('#route-next').onclick=()=>selectStep((active+1)%4);"
s=s.replace(target,target+'''
 const mountVersion=++campusMountVersion;
 import('./campus3d.js').then(({mountCampus})=>{if(mountVersion!==campusMountVersion)return;const container=document.querySelector('#campus-3d');if(!container)return;document.querySelector('#scene-loading')?.remove();campusView=mountCampus(container,v.hostel);if(active)campusView.setStep(active)}).catch(()=>{if(mountVersion===campusMountVersion){const loading=document.querySelector('#scene-loading');if(loading)loading.textContent='Unable to load the 3D view. Refresh the page to try again.'}});
''')
s=s.replace("function render(){const route=", "function render(){campusMountVersion++;campusView?.dispose();campusView=null;const route=")
p.write_text(s,encoding='utf-8')
