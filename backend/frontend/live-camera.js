window.LiveCamera=(()=>{
 let stream=null,current=null,timer=null;
 function stop(){clearTimeout(timer);timer=null;stream?.getTracks().forEach(t=>t.stop());stream=null;if(current){current.video.srcObject=null;current.scan.disabled=true;current.stop.disabled=true;current.note.textContent='Camera stopped.'}current=null;}
 window.addEventListener('hashchange',stop);
 async function attach({request,lookup,safe}){
  stop();const host=document.querySelector('.camera');if(!host)return;
  host.style.height='auto';host.style.minHeight='280px';host.style.display='block';host.style.padding='16px';
  host.innerHTML=`<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><strong>${gate==='entry'?'ENTRY':'EXIT'} CAMERA</strong><span id="camera-runtime-status">Checking recognition service…</span></div><div style="position:relative"><video id="gate-camera-video" autoplay muted playsinline style="display:block;width:100%;max-height:360px;min-height:160px;background:#111;border-radius:8px;object-fit:contain"></video><div aria-hidden="true" style="position:absolute;left:10%;top:36%;width:80%;height:28%;border:2px solid #52e6b3;border-radius:6px;pointer-events:none"></div></div><label style="display:block;margin-top:12px"><input type="checkbox" id="camera-auto" checked> Automatically detect and read number plates</label><div class="actions" style="margin:14px 0"><button class="btn" id="camera-start">Start camera</button><button class="btn secondary" id="camera-stop" disabled>Stop camera</button><button class="btn" id="camera-recognize" disabled>Recognize current frame</button></div><p id="camera-message" style="margin:8px 0;font-size:13px" role="status">Start the camera and allow access. Hold the plate clearly inside the green guide; two matching readings fill the field automatically.</p><span id="plate-preview" hidden style="display:none">—</span>`;
  const video=host.querySelector('video'),start=host.querySelector('#camera-start'),end=host.querySelector('#camera-stop'),scan=host.querySelector('#camera-recognize'),note=host.querySelector('#camera-message');
  const session={video,scan,stop:end,note};current=session;let runtime=null,busy=false,lastRead=null,repeatCount=0,editVersion=0;
  document.querySelector('#plate-input').addEventListener('input',()=>{editVersion++;lastRead=null;repeatCount=0;host.querySelector('#camera-auto').checked=false;clearTimeout(timer)});
  const observer=new MutationObserver(()=>{if(!host.isConnected){if(current===session)stop();observer.disconnect()}});observer.observe(document.querySelector('#app'),{childList:true,subtree:true});
  function schedule(){clearTimeout(timer);if(stream&&current===session&&host.isConnected&&host.querySelector('#camera-auto').checked)timer=setTimeout(async()=>{await scan.onclick();if(stream&&host.isConnected&&host.querySelector('#camera-auto').checked)schedule()},2200)}
  host.querySelector('#camera-auto').onchange=schedule;
  async function check(){runtime=await request('/api/v1/anpr/camera-status');if(!host.isConnected)return;host.querySelector('#camera-runtime-status').textContent=runtime.message;scan.disabled=!stream||!runtime.ready;}
  start.onclick=safe(async()=>{
   if(!navigator.mediaDevices?.getUserMedia)throw Error('Camera requires localhost or HTTPS and a browser with camera support.');
   let incoming;try{incoming=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720},facingMode:{ideal:'environment'}},audio:false})}catch(err){note.textContent=err.name==='NotAllowedError'?'Camera permission denied. Allow camera access in the browser and try again.':'Camera unavailable. Connect a webcam or choose manual plate entry.';return}
   if(!host.isConnected||current!==session){incoming.getTracks().forEach(t=>t.stop());return}
   stream?.getTracks().forEach(t=>t.stop());stream=incoming;video.srcObject=stream;await video.play();end.disabled=false;await check();note.textContent=runtime.ready?'Hold the plate inside the green guide. Keep it steady until the number appears below.':'Live preview ready. Recognition is not enabled on the backend; manual plate entry remains available.';if(runtime.ready)schedule();
  });
  end.onclick=()=>{stop();current=session;};
  scan.onclick=async(event)=>{
   const automatic=!event,capturedEditVersion=editVersion;
   if(busy||current!==session||!stream||!runtime?.ready)return;
   if(!video.videoWidth){note.textContent='Wait until the camera image appears.';return}
   busy=true;scan.disabled=true;note.textContent='Recognizing plate…';
   try{
    const canvas=document.createElement('canvas'),scale=Math.min(1,1280/video.videoWidth);canvas.width=Math.round(video.videoWidth*scale);canvas.height=Math.round(video.videoHeight*scale);canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
    const result=await request('/api/v1/anpr/frames',{image:canvas.toDataURL('image/jpeg',.8).split(',')[1],direction:gate,gate_id:'MAIN'});
    if(!host.isConnected||current!==session||capturedEditVersion!==editVersion)return;
    if(!result.detection){lastRead=null;repeatCount=0;note.textContent=result.message;return}
    const read=result.detection;
    if(automatic){repeatCount=lastRead===read.plate?repeatCount+1:1;lastRead=read.plate;if(repeatCount<2){note.textContent='Reading '+read.plate+' — keep the plate steady to confirm.';return}}
    host.querySelector('#camera-auto').checked=false;clearTimeout(timer);document.querySelector('#plate-input').value=read.plate;document.querySelector('#plate-preview').textContent=read.plate;originalPlate=read.plate_raw;note.textContent='Detected '+read.plate+' · '+Math.round(read.confidence*100)+'% score. Verify the visible plate, inspection and people count before passage.';await lookup();
   }catch(err){if(host.isConnected)note.textContent=err.message}finally{busy=false;if(host.isConnected)scan.disabled=!stream||!runtime?.ready}
  };
  try{await check()}catch(err){if(host.isConnected)host.querySelector('#camera-runtime-status').textContent=err.message}
 }
 return {attach,stop,get active(){return !!stream}};
})();
