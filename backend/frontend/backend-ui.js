// Authenticated integration: all durable actions are validated by the API.

window.SharedState=(()=>{

 let user=null,status='Connecting',started=false,offline=false,polling=false;

 const tokens=()=>{try{return JSON.parse(sessionStorage.getItem('campus-tracking')||'{}')}catch{return {}}};

 function connectionBanner(disconnected){

  offline=disconnected;

  if(disconnected){status='Connection unavailable';if(!document.querySelector('#backend-offline')){const banner=document.createElement('section');banner.id='backend-offline';banner.className='panel';banner.setAttribute('role','alert');banner.style.border='2px solid #bf0054';banner.innerHTML='<strong>Backend connection unavailable</strong><p>Displayed records may be out of date. Changes are paused until the connection returns.</p><button class="btn secondary" id="backend-retry">Retry connection</button>';app.prepend(banner);banner.querySelector('button').onclick=safe(async()=>{await request('/api/v1/health');await refresh()})}document.querySelectorAll('#app button:not(#backend-retry):not(#camera-stop):not([data-head-tab]):not([data-monitor-tab]):not([data-head-section]),#app input,#app textarea,#app select:not(#head-view)').forEach(el=>{if(!el.disabled){el.dataset.backendOffline='true';el.disabled=true}})}

  else{document.querySelector('#backend-offline')?.remove();document.querySelectorAll('[data-backend-offline]').forEach(el=>{el.disabled=false;delete el.dataset.backendOffline})}

 }

 async function request(path,body,method='POST',headers={}){

  let r;try{r=await fetch(path,{method:body===undefined?'GET':method,credentials:'same-origin',signal:AbortSignal.timeout(path==='/api/v1/anpr/frames'?60000:path.includes('/ai/')?45000:10000),headers:{...(body===undefined?{}:{'Content-Type':'application/json'}),...headers},body:body===undefined?undefined:JSON.stringify(body)});}catch(err){connectionBanner(true);throw Error('Backend could not be reached. Retry the connection before making changes.')}if(r.status>=500&&!path.includes('/ai/')&&path!=='/api/v1/anpr/frames')connectionBanner(true);else connectionBanner(false);

  const d=await r.json();if(r.status===401&&user){user=null;render();}if(!r.ok)throw Error(Array.isArray(d.detail)?d.detail.map(x=>x.msg).join('; '):d.detail||d.error||'Request failed');return d;

 }

 async function refresh(redraw=true){

  if(user&&!location.hash.startsWith('#visitor')){const d=await request('/api/v1/state');visits=d.state.visits;logs=d.state.logs;incidents=d.state.incidents;headSettings={...d.state.headSettings,source:'browser'};headSource='browser'}

  else{visits=[];for(const [id,t] of Object.entries(tokens())){try{visits.push(await request('/api/v1/public/visits/'+id,undefined,'GET',{'X-Visit-Token':t}))}catch{}}logs=[];incidents=[]}

  status='Up to date';if(redraw)render();

 }

 function safe(fn){return async e=>{e?.preventDefault();const b=e?.currentTarget?.tagName==='BUTTON'?e.currentTarget:e?.currentTarget?.querySelector('button');if(b)b.disabled=true;try{await fn(e)}catch(err){toast(err.message)}finally{if(b?.isConnected&&!b.dataset.backendOffline)b.disabled=false}}}

 function staffBar(){

  document.querySelectorAll('[data-sync-status]').forEach(el=>el.remove());

  let area=document.querySelector('#backend-staff');if(!area){area=document.createElement('span');area.id='backend-staff';document.querySelector('nav').append(area)}

  area.innerHTML=user?`${['head','admin','security'].includes(user.role)?'<a href="#registry">Registered vehicles</a> · ':''}<span>${esc(user.name)}</span> <button class="btn secondary table-btn" id="staff-logout">Sign out</button>`:'<a href="#head">Staff sign in</a>';

  document.querySelector('#staff-logout')?.addEventListener('click',safe(async()=>{await request('/api/v1/auth/logout',{});user=null;await refresh()}));

 }

 function loginView(role){

  app.innerHTML=heading('STAFF ACCESS','Staff <span>sign in</span>','Use your assigned staff account.')+`<section class="panel" style="max-width:540px;margin:auto"><h2>${esc(role)} access</h2><form id="staff-login">${role==='warden'?'<label class="field">Assigned warden<select name="warden_id"><option value="MENON">Dr. R. Menon  -  Gauthama</option><option value="DEVI">Dr. S. Devi  -  Mythreyi / Gargi</option></select></label>':''}<label class="field">Username<input name="username" required autocomplete="username"></label><label class="field" style="margin-top:16px">Password<input name="password" type="password" required autocomplete="current-password"></label><button class="btn" style="margin-top:18px">Sign in</button></form></section>`;

  document.querySelector('#staff-login').onsubmit=safe(async e=>{user=(await request('/api/v1/auth/login',{...Object.fromEntries(new FormData(e.target)),portal:role})).user;await refresh()});

 }

 async function loadTracking(id){

  const t=tokens()[id];if(!user&&!t)throw Error('Enter the private tracking token issued with this request.');

  const v=await request(t?'/api/v1/public/visits/'+id:'/api/v1/visits/'+id,undefined,'GET',t?{'X-Visit-Token':t}:{});const i=visits.findIndex(x=>x.id===id);if(i<0)visits.push(v);else visits[i]=v;return v;

 }

 async function registryView(target){

  // When a target is given the registry renders inside the Security head page (no separate page heading / back links).

  const embedded=!!target,out=target||app,top=t=>embedded?'':t;

  out.innerHTML=top(heading('REPEAT CAMPUS ACCESS','Registered <span>vehicles</span>','Faculty, staff and approved daily visitors do not need a new warden request. Every entry still requires physical vehicle inspection.'))+'<section class="panel">Loading registrations…</section>';

  try{

   const {items}=await request('/api/v1/registered-vehicles');if(!embedded&&location.hash!=='#registry')return;const manage=['head','admin'].includes(user.role);

   out.innerHTML=top(heading('REPEAT CAMPUS ACCESS','Registered <span>vehicles</span>','An exact plate match to an active registration gives entry permission. Guards verify occupants and inspect the vehicle before recording passage.'))+

    (manage?`<section class="panel"><h2>Approve a regular vehicle</h2><form id="registration-form"><div class="form-grid"><label class="field">Vehicle number<input name="plate" required maxlength="16" placeholder="TN 38 AB 1234"></label><label class="field">Owner / approved visitor name<input name="owner_name" required maxlength="100"></label><label class="field">Category<select name="category"><option>Faculty</option><option>Staff</option><option>Approved daily visitor</option><option>Vendor</option></select></label><label class="field">Valid until<input name="valid_until" type="date" min="${today()}" required></label><label class="field">Reason for regular access<input name="purpose" required minlength="3" maxlength="180" placeholder="Faculty campus access"></label></div><button class="btn" style="margin-top:18px">Approve registration</button></form></section>`:'')+

    `<section class="panel" style="margin-top:22px"><h2>Approved vehicle list</h2><div class="table-scroll"><table><thead><tr><th>Vehicle</th><th>Owner</th><th>Category / purpose</th><th>Expiry</th><th>Permission</th>${manage?'<th>Action</th>':''}</tr></thead><tbody>${items.map(r=>`<tr data-registry-row="${esc(r.id)}"><td><strong>${esc(r.plate)}</strong></td><td>${esc(r.owner_name)}</td><td>${esc(r.category)}<br><small>${esc(r.purpose)}</small></td><td>${esc(r.valid_until)}</td><td>${r.eligible?'Active':!r.active?'Suspended':'Expired'}</td>${manage?`<td><button class="btn secondary table-btn" data-registration="${esc(r.id)}">${r.active?'Suspend':'Activate'}</button></td>`:''}</tr>`).join('')||'<tr><td colspan="6" class="empty">No vehicles registered yet.</td></tr>'}</tbody></table></div><p class="hint">Registration approvals, inspections and passage times are recorded in the database.</p>${embedded?'':`<a href="${user.role==='security'?'#security':'#head'}">Return to dashboard →</a>`}</section>`;

   const table=document.querySelector('[data-registry-row]')?.closest('table')||document.querySelector('table');table.closest('.table-scroll').insertAdjacentHTML('beforebegin',`<div class="head-inputs"><label class="field">Search registered vehicles<input id="registry-search" placeholder="Plate, owner, category or purpose"></label><label class="field">Registration status<select id="registry-status"><option value="">All registrations</option><option value="active">Active</option><option value="suspended">Suspended</option><option value="expired">Expired</option></select></label><button class="btn secondary" id="registry-export">Export filtered CSV</button></div><p class="hint" id="registry-count">${items.length} registrations</p>`);

   const matching=()=>{const q=document.querySelector('#registry-search').value.trim().toLowerCase(),permission=document.querySelector('#registry-status').value;return items.filter(r=>(!q||(r.plate+' '+r.owner_name+' '+r.category+' '+r.purpose).toLowerCase().includes(q))&&(!permission||(r.eligible?'active':!r.active?'suspended':'expired')===permission))};

   const filterRegistry=()=>{const matches=matching();table.querySelectorAll('[data-registry-row]').forEach(row=>row.hidden=!matches.some(r=>r.id===row.dataset.registryRow));document.querySelector('#registry-count').textContent=matches.length+' matching registrations'};

   document.querySelector('#registry-search').oninput=filterRegistry;document.querySelector('#registry-status').onchange=filterRegistry;document.querySelector('#registry-export').onclick=()=>HeadMonitor.exportCSV('registered-vehicles.csv',['plate','owner_name','category','purpose','valid_until','active','approved_by'],matching());

   document.querySelector('#registration-form')?.addEventListener('submit',safe(async e=>{await request('/api/v1/registered-vehicles',Object.fromEntries(new FormData(e.target)));toast('Vehicle registration approved.');await registryView(target)}));

   document.querySelectorAll('[data-registration]').forEach(b=>b.onclick=safe(async()=>{const r=items.find(x=>x.id===b.dataset.registration);await request('/api/v1/registered-vehicles/'+r.id,{active:!r.active,version:r.version},'PATCH');await registryView(target)}));

  }catch(e){toast(e.message)}

 }

 function personCount(expected=null){

  const field=document.querySelector('#person-count'),value=Number(field?.value);

  if(!field?.value||!Number.isInteger(value)||value<1||value>100)throw Error('Enter the number of people in the vehicle, including the driver (1 - 100).');

  if(gate==='exit'&&expected===null)throw Error('Entry passenger count is missing. Contact the security head.');

  if(gate==='exit'&&value!==expected)throw Error('Passenger count mismatch: entry '+expected+', exit '+value+'. Recheck all occupants before departure.');

  return value;

 }

 function bindPersonCheck(expected=null){

  const field=document.querySelector('#person-count'),hint=document.querySelector('#person-count-check');if(!field)return;

  const draw=()=>{const b=document.querySelector('#confirm-passage')||document.querySelector('#regular-passage');try{personCount(expected);if(b)b.disabled=false;hint.textContent=gate==='exit'?'Count matches entry. Guard must verify the occupants.':'Count will be saved with the entry record.';hint.style.color='#16734b'}catch(err){if(b)b.disabled=true;hint.textContent=(gate==='exit'?'Entry count: '+(expected??'not recorded')+'. ':'')+err.message;hint.style.color='#bf0054'}};

  field.oninput=draw;draw();

 }

 async function registeredLookup(p){

  const result=document.querySelector('#gate-result');let d;try{d=await request('/api/v1/registered-vehicles/lookup/'+p)}catch(e){result.innerHTML='<div class="result-banner bad">No active visit or registered vehicle found.<br><small>Check the visible plate. A visitor request or approved registration is required.</small></div>';return}

  const {vehicle:r,inside}=d,entry=gate==='entry',allowed=entry?r.eligible&&!inside:!!inside;

  result.innerHTML=`<div class="result-banner ${allowed?'good':'bad'}"><strong>${allowed?entry?'Registered vehicle — entry permitted':'Registered vehicle — departure permitted':inside&&entry?'Vehicle already inside':!entry?'No recorded entry':!r.active?'Registration suspended':'Registration expired'}</strong><br><small>${entry?'No new warden request is needed. Physical inspection remains mandatory.':'Departure is recorded against the registered entry.'}</small></div><div class="result-details">${[['Owner / visitor',r.owner_name],['Vehicle',r.plate],['Category',r.category],['Purpose',r.purpose],['Valid until',r.valid_until],['Approved by',r.approved_by]].map(([k,v])=>`<div><span>${k}</span><strong>${esc(v)}</strong></div>`).join('')}</div>${allowed?`${entry?'<label class="check"><input id="regular-inspected" type="checkbox">Required physical vehicle inspection completed.</label>':''}<label class="check"><input id="regular-verified" type="checkbox">Visible plate and occupant match this registration; vehicle is passing the gate.</label><button class="btn" id="regular-passage" style="margin-top:18px">Record ${entry?'entry':'departure'} →</button>`:''}`;

  bindPersonCheck(inside?.entry_person_count??null);

  document.querySelector('#regular-passage')?.addEventListener('click',safe(async()=>{

   const person_count=personCount(inside?.entry_person_count??null);if(plate(document.querySelector('#plate-input').value)!==p)throw Error('Plate changed. Check permission again.');const visitor_verified=document.querySelector('#regular-verified').checked;if(!visitor_verified)throw Error('Verify the plate and occupant first.');

   if(entry){const inspection_completed=document.querySelector('#regular-inspected').checked;if(!inspection_completed)throw Error('Complete the mandatory inspection first.');await request('/api/v1/registered-vehicles/'+r.id+'/entry',{version:r.version,plate:p,visitor_verified,inspection_completed,person_count})}

   else await request('/api/v1/registered-passages/'+inside.id+'/exit',{version:inside.version,plate:p,visitor_verified,person_count});await refresh();toast(entry?'Registered vehicle entry recorded.':'Registered vehicle departure recorded.');

  }));

 }

 async function cyclePanel(){

  const host=document.querySelector('#passage-monitor');if(!host)return;

  try{const {items}=await request('/api/v1/barrier-cycles');if(!host.isConnected)return;

   host.innerHTML='<h2>Passage count & tailgating alerts</h2><p class="hint">Sensor simulation: one approval covers one vehicle. A count above one raises an alert and blocks further entry recording until a guard investigates. Vehicle-count sensors and physical barrier controls are not connected.</p>'+items.slice(0,8).map(c=>`<div style="padding:15px 0;border-top:1px solid #e4e5ec"><strong>${esc(c.plate)}</strong> · ${esc(c.status==='alert'?'TAILGATING ALERT':c.status.replace('_',' '))}<br><small>Approved: ${c.authorized_count} · Counted: ${c.detected_count} · ${stamp(c.opened_at)}</small>${user.role==='security'&&c.status==='awaiting_count'?`<div class="actions"><button class="btn secondary table-btn" data-count-cycle="${c.id}" data-count="1">Simulate 1 vehicle</button><button class="btn table-btn" data-count-cycle="${c.id}" data-count="2">Simulate tailgating (2)</button></div>`:''}${c.status==='alert'?`<p>Check the additional vehicle and its occupants. Another entry cannot be recorded until this alert is resolved.</p><button class="btn secondary" data-resolve-cycle="${c.id}">Record investigation outcome</button>`:''}${c.resolution_note?'<p>'+esc(c.resolution_note)+'</p>':''}</div>`).join('')||(items.length?'':'<p>No passage cycles recorded yet.</p>');

   host.querySelectorAll('[data-count-cycle]').forEach(b=>b.onclick=safe(async()=>{const c=items.find(x=>x.id===b.dataset.countCycle);await request('/api/v1/barrier-cycles/'+c.id+'/count',{version:c.version,detected_count:Number(b.dataset.count)});await refresh();}));

   host.querySelectorAll('[data-resolve-cycle]').forEach(b=>b.onclick=()=>{const c=items.find(x=>x.id===b.dataset.resolveCycle);b.insertAdjacentHTML('afterend',`<form class="tail-outcome"><label class="field">Investigation outcome<textarea name="note" required minlength="10" maxlength="500" placeholder="What was checked and what happened?"></textarea></label><button class="btn">Save outcome and resolve alert</button></form>`);b.disabled=true;const f=b.nextElementSibling;f.onsubmit=safe(async()=>{await request('/api/v1/barrier-cycles/'+c.id+'/resolve',{version:c.version,note:new FormData(f).get('note')});await refresh();});});

  }catch(e){host.textContent=e.message}

 }

 function addCycles(){const host=document.createElement('section');host.className='panel';host.id='passage-monitor';host.style.marginTop='22px';const anchor=document.querySelector('.security-grid');if(anchor)app.insertBefore(host,anchor);else app.append(host);cyclePanel()}

 async function detectionPanel(){

  const anchor=document.querySelector('.security-grid');if(!anchor)return;const host=document.createElement('section');host.className='panel';host.style.margin='22px 0';anchor.before(host);

  try{const {items}=await request('/api/v1/anpr/detections');if(!host.isConnected)return;host.innerHTML='<h2>Latest ANPR output</h2>'+(items.length?items.slice(0,3).map(p=>`<p><strong>${esc(p.plate)}</strong> · ${Math.round(p.confidence*100)}% confidence · ${esc(p.direction)} · ${stamp(p.captured_at)} <button class="btn secondary table-btn" data-detection-id="${p.id}">Check this plate</button></p>`).join(''):'<p class="hint">No plate readings yet. Start the camera and hold a number plate in view.</p>');host.querySelectorAll('[data-detection-id]').forEach(b=>b.onclick=safe(async()=>{const p=items.find(x=>x.id===b.dataset.detectionId);gate=p.direction;security();document.querySelector('#plate-input').value=p.plate;document.querySelector('#plate-preview').textContent=p.plate;await lookup()}));}catch(e){host.textContent=e.message}

 }

 function wire(){

  const originalHeading=heading;heading=function(...args){return originalHeading(...args).replace(/<small[^>]*data-sync-status[^>]*>[\s\S]*?<\/small>/g,'')};

  const oldRender=render,oldVisitor=visitor,oldWarden=warden,oldSecurity=security,oldLookup=lookup,oldHead=securityHead,oldTracking=showTracking,oldReport=reportIncident,oldBind=bindIncidents;

  render=function(){

   const role=({'#warden':'warden','#security':'security','#head':'head','#registry':'registry'})[location.hash];

   if(role&&!user){loginView(role);staffBar();return}

   if(role&&!(role==='registry'&&['head','admin','security'].includes(user.role))&&user.role!==role&&!(role==='head'&&user.role==='admin')){loginView(role);document.querySelector('.page-heading p').textContent='Sign in to switch to this portal. Your current account belongs to another staff role.';staffBar();return}

   if(role==='registry'){registryView();staffBar();return}oldRender();staffBar();document.querySelectorAll('.notice p span').forEach(x=>{if(x.textContent.includes('saved in this browser'))x.textContent='Records are stored in the backend database. Camera recognition is simulated.'});

  };

  visitor=function(){oldVisitor();const f=document.querySelector('#visit-form'),field=f.elements.studentId;let timer;

   field.oninput=()=>{clearTimeout(timer);document.querySelector('#submit-visit').disabled=true;timer=setTimeout(async()=>{try{const r=await request('/api/v1/students/'+encodeURIComponent(field.value.trim().toUpperCase()));for(const k of ['student','branch','hostel','warden'])f.elements[k].value=r[k];document.querySelector('#student-lookup-status').textContent='Student found in the backend directory.';document.querySelector('#submit-visit').disabled=false}catch(e){for(const k of ['student','branch','hostel','warden'])f.elements[k].value='';document.querySelector('#student-lookup-status').textContent=e.message}},180)};

   document.querySelectorAll('[data-student-id]').forEach(b=>b.onclick=()=>{field.value=b.dataset.studentId;field.oninput()});

   f.onsubmit=safe(async()=>{const vals=Object.fromEntries(new FormData(f)),body={};for(const k of ['visitor','phone','relation','plate','studentId','purpose','date','vehicleType'])body[k]=vals[k];const d=await request('/api/v1/visits',body),saved=tokens();saved[d.visit.id]=d.tracking_token;sessionStorage.setItem('campus-tracking',JSON.stringify(saved));await refresh(false);if(!visits.some(v=>v.id===d.visit.id))visits.unshift(d.visit);f.reset();document.querySelector('#submit-visit').disabled=true;document.querySelector('#student-lookup-status').textContent='Enter a student ID for a new request.';sessionStorage.setItem('campus-last-request',d.visit.id);document.querySelector('#track-id').value=d.visit.id;oldTracking(d.visit.id);document.querySelector('#track-result').insertAdjacentHTML('beforeend',`<details><summary>Save your private tracking token</summary><p style="overflow-wrap:anywhere">${esc(d.tracking_token)}</p></details>`);toast('Request submitted. Save your request ID and tracking token.');});

   document.querySelector('#track-form').onsubmit=safe(async()=>{const id=document.querySelector('#track-id').value.trim().toUpperCase();if(!tokens()[id]&&!user){const t=prompt('Enter the private tracking token');if(!t)return;const saved=tokens();saved[id]=t.trim();sessionStorage.setItem('campus-tracking',JSON.stringify(saved))}await loadTracking(id);sessionStorage.setItem('campus-last-request',id);oldTracking(id)});

   const last=sessionStorage.getItem('campus-last-request');if(last&&visits.some(v=>v.id===last)){document.querySelector('#track-id').value=last;oldTracking(last)}

  };

  showTracking=async id=>{try{await loadTracking(id);sessionStorage.setItem('campus-last-request',id);oldTracking(id)}catch(e){toast(e.message)}};

  warden=function(){viewFilter=user.name;oldWarden();const select=document.querySelector('#warden-filter');select.innerHTML=`<option>${esc(user.name)}</option>`;select.disabled=true;select.closest('section').querySelector('p.hint').textContent='Only visits assigned to your authenticated account are shown.';

   const closed=visits.filter(v=>['expired','rejected'].includes(effective(v))).length;

   const counts=[['Total visits',visits.length],['Awaiting entry approval',visits.filter(v=>effective(v)==='pending').length],['Entry approved',visits.filter(v=>effective(v)==='approved').length],['Inside campus',visits.filter(v=>['inside','exit'].includes(v.status)).length],['Completed visits',visits.filter(v=>v.status==='completed').length],['Rejected / expired',closed]];

   document.querySelector('.stats').innerHTML=counts.map(([label,count])=>`<div class="stat"><strong>${count}</strong><span>${label}</span></div>`).join('');

   document.querySelector('.stats').style.gridTemplateColumns='repeat(auto-fit,minmax(160px,1fr))';

   select.closest('section').querySelector('h2').textContent='Requests & visit history';

   app.insertAdjacentHTML('beforeend',`<section class="panel" style="margin-top:22px"><div class="head-title"><h2>Approval & gate history</h2><button class="btn secondary" id="warden-refresh">Refresh records</button></div><p class="hint">Every action is linked to the same request ID shown above. Inside campus includes visitors awaiting departure or already cleared to leave.</p><div class="table-scroll"><table><thead><tr><th>Time (IST)</th><th>Request / vehicle</th><th>Action</th><th>Recorded by</th></tr></thead><tbody>${logs.map(l=>`<tr><td>${stamp(l.time)}</td><td>${esc(l.visit)}<br>${esc(l.plate)}</td><td>${esc(l.action)}<br><small>${esc(l.note||'')}</small></td><td>${esc(l.actor)}</td></tr>`).join('')||'<tr><td colspan="4" class="empty">No visit activity yet.</td></tr>'}</tbody></table></div></section>`);

   document.querySelector('#warden-refresh').onclick=safe(async()=>{await refresh();toast('Visit records refreshed.');});

   document.querySelectorAll('[data-action]').forEach(b=>b.onclick=safe(async()=>{const v=visits.find(x=>x.id===b.dataset.id),exit=b.dataset.action==='exit',verified=exit?document.querySelector(`[data-verify="${v.id}"]`).checked:false;if(exit&&!verified)throw Error('Verify the visitor and student first.');await request('/api/v1/visits/'+v.id+'/'+(exit?'exit-approval':'entry-approval'),{version:v.version,decision:b.dataset.action==='reject'?'reject':'approve',meeting_verified:verified});await refresh();toast('Approval recorded.')}));

  };

  lookup=async function(){foundId=null;document.querySelector('#gate-result').innerHTML='<div class="result-banner">Checking the latest approval...</div>';try{

   await refresh(false);const config=await request('/api/v1/access-policy');if(gate==='entry'&&(config.mode==='lockdown'||visits.filter(v=>v.entered&&!v.exited).length>=config.capacity)){document.querySelector('#gate-result').innerHTML='<div class="result-banner bad"><strong>'+ (config.mode==='lockdown'?'Campus entry paused':'Campus vehicle capacity is full')+'</strong><br><small>Contact the security head. Departure checks remain available.</small></div>';return}const input=document.querySelector('#plate-input'),query=input.value.trim().toUpperCase();foundId=null;

   if(!query)throw Error('Enter a vehicle number or request ID.');

   const byId=query.startsWith('AMV-');let selected=null;

   if(byId){selected=await request('/api/v1/visits/'+encodeURIComponent(query));const i=visits.findIndex(v=>v.id===selected.id);if(i<0)visits.push(selected);else visits[i]=selected;}

   const p=selected?selected.plate:plate(query);input.value=p;if(!originalPlate)document.querySelector('#plate-preview').textContent=p;

   const normal=selected?[selected]:visits.filter(v=>v.access_type!=='registered'&&v.plate===p&&(gate==='exit'?['inside','exit'].includes(v.status):v.date===today()&&!['completed','rejected'].includes(v.status)));

   if(!normal.length){await registeredLookup(p);return}

   if(selected&&(gate==='entry'?selected.date!==today()||['completed','rejected'].includes(selected.status):!['inside','exit'].includes(selected.status))){document.querySelector('#gate-result').innerHTML=`<div class="result-banner bad"><strong>${esc(effective(selected)==='expired'?'Visit expired':selected.status==='completed'?'Visit already completed':selected.status==='rejected'?'Request rejected':gate==='entry'?'Visit is scheduled for '+selected.date:'Vehicle has not entered campus')}</strong><br><small>This request cannot authorize ${gate==='entry'?'entry':'departure'} now.</small></div><p>${esc(selected.id)}  /  ${esc(selected.plate)}<br>${esc(selected.visitor)}  /  ${esc(selected.student)}<br>Assigned warden: ${esc(selected.warden)}</p>`;return}

   const all=visits;try{visits=normal;oldLookup()}finally{visits=all}

   const result=document.querySelector('#gate-result'),match=visits.find(v=>v.id===foundId);

   if(match)result.insertAdjacentHTML('beforeend',`<div class="result-details">${[['Entry approval',match.entryApproval?match.entryApproval.decision+'  /  '+match.entryApproval.by+'  /  '+stamp(match.entryApproval.at):'Awaiting warden decision'],['Exit approval',match.exitApproval?match.exitApproval.decision+'  /  '+match.exitApproval.by+'  /  '+stamp(match.exitApproval.at):'Not cleared for departure'],['Entry occupants',match.entry_person_count??'Not recorded'],['Exit recorded',stamp(match.exited)]].map(([k,v])=>`<div><span>${k}</span><strong>${esc(v)}</strong></div>`).join('')}</div>`);

   const b=document.querySelector('#confirm-passage');const matched=visits.find(x=>x.id===foundId);bindPersonCheck(matched?.entry_person_count??null);if(!b)return;b.onclick=safe(async()=>{const id=foundId;let v=visits.find(x=>x.id===id);const person_count=personCount(v.entry_person_count??null);const visible=document.querySelector('#plate-input').value,verified=document.querySelector('#guard-verified').checked;if(!verified)throw Error('Verify the visible plate and visitor first');if(gate==='entry'){if(!document.querySelector('#inspection-verified').checked)throw Error('Complete the physical inspection first');v=await request('/api/v1/visits/'+id+'/inspection',{version:v.version,passed:true,note:'Required physical vehicle inspection completed'})}await request('/api/v1/visits/'+id+'/'+gate,{version:v.version,plate:visible,visitor_verified:verified,gate_id:'MAIN',original_plate:originalPlate||visible,person_count});originalPlate='';await refresh();toast('Passage recorded.');});

  }catch(e){document.querySelector('#gate-result').innerHTML='<div class="result-banner bad">'+esc(e.message)+'</div>';toast(e.message)}};

  security=function(){oldSecurity();const plateField=document.querySelector('#plate-input');plateField.maxLength=64;plateField.placeholder='Vehicle number or AMV request ID';plateField.closest('label').firstChild.textContent='Recognized plate / request ID / guard correction';LiveCamera.attach({request,lookup,safe});document.querySelector('.section-label span').textContent='Camera / plate recognition';document.querySelector('.scan-controls')?.remove();document.querySelector('#plate-input').closest('label').insertAdjacentHTML('afterend',`<label class="field" style="margin-top:18px">Number of people ${gate==='entry'?'entering':'leaving'} (including driver)<input id="person-count" type="number" min="1" max="100" step="1" required placeholder="Guard: count all occupants"></label><p class="hint" id="person-count-check">${gate==='entry'?'Count everyone in the vehicle before confirming entry.':'Count everyone again. The exit count must equal the saved entry count.'}</p>`);const quick=document.createElement('section');quick.className='panel';quick.style.margin='18px 0';quick.innerHTML='<div class="head-title"><div><h2>Registered vehicles</h2><p class="hint">Look up faculty, staff and approved daily visitors. Active registration replaces a new warden request; inspection remains required.</p></div><a class="btn" href="#registry">Open registered vehicles →</a></div>';document.querySelector('.page-heading').after(quick);addCycles();detectionPanel();document.querySelector('#lookup').textContent='Check approval / registered access →';};

  securityHead=function(){const selected=headTab;if(['occupancy','reads','policy','registry'].includes(selected))headTab='overview';oldHead();headTab=selected;if(['occupancy','reads','policy','registry'].includes(selected))document.querySelectorAll('[data-head-tab]').forEach(b=>b.classList.remove('active'));addCycles();headSource='browser';const source=document.querySelector('#head-source');source.value='browser';source.disabled=true;

   if(document.querySelector('#queue-form'))document.querySelector('#queue-form').onsubmit=safe(async e=>{const vals=Object.fromEntries(new FormData(e.target));await request('/api/v1/settings',{waiting:Number(vals.waiting),lanes:Number(vals.lanes),seconds:Number(vals.seconds),dwell:headSettings.dwell},'PATCH');await refresh()});

   if(document.querySelector('#head-threshold'))document.querySelector('#head-threshold').onclick=safe(async()=>{await request('/api/v1/settings',{waiting:headSettings.waiting,lanes:headSettings.lanes,seconds:headSettings.seconds,dwell:Number(document.querySelector('#head-dwell').value)},'PATCH');await refresh()});

   if(document.querySelector('#head-summary'))document.querySelector('#head-summary').onclick=safe(async()=>{const date=document.querySelector('#head-report-date').value,d=await request('/api/v1/ai/summary',{date});document.querySelector('#head-report').innerHTML='<small>AI-assisted briefing · database records</small><h3>Daily briefing · '+esc(date)+'</h3>'+d.facts.map(f=>'<p>'+esc(f.text)+'</p>').join('')});

   document.querySelectorAll('[data-head-review]').forEach(b=>b.onclick=()=>reportIncident(b.dataset.headReview.split(':')[0]));document.querySelector('#head-refresh').onclick=safe(async()=>{await refresh();toast('Monitoring refreshed.');});HeadMonitor.attach({request,safe,refresh,user,registry:registryView});

  };

  reportIncident=function(id,flag=null){if(visits.find(v=>v.id===id)?.access_type==='registered'){toast('Registered access concerns can be handled by suspending the registration.');return}oldReport(id,flag);const f=document.querySelector('#incident-report');if(f)f.onsubmit=safe(async()=>{await request('/api/v1/incidents',{visit_id:id,...Object.fromEntries(new FormData(f))});document.querySelector('#head-dialog').close();await refresh();toast('Concern assigned.');});};

  bindIncidents=function(role){oldBind(role);document.querySelectorAll('[data-incident-action]').forEach(b=>b.addEventListener('click',()=>{const f=document.querySelector('#incident-update');if(f)f.onsubmit=safe(async()=>{const i=incidents.find(x=>x.id===b.dataset.incidentAction);await request('/api/v1/incidents/'+i.id+'/actions',{version:i.version,...Object.fromEntries(new FormData(f))});document.querySelector('#incident-dialog').close();await refresh();toast('Investigation action saved.');});}));};

 }

 async function start(){if(started)return;started=true;wire();try{user=await request('/api/v1/auth/me')}catch{user=null}try{await refresh()}catch(e){status='Connection unavailable';toast(e.message)}setInterval(async()=>{if(polling||window.LiveCamera?.active)return;const recovering=offline,el=document.activeElement;if(!recovering&&((el&&['INPUT','TEXTAREA','SELECT'].includes(el.tagName))||document.querySelector('dialog[open]')))return;polling=true;try{if(recovering){await request('/api/v1/health');try{user=await request('/api/v1/auth/me')}catch{user=null}}const before=JSON.stringify({visits,logs,incidents,headSettings});await refresh(false);if(recovering||before!==JSON.stringify({visits,logs,incidents,headSettings}))render();document.querySelectorAll('[data-sync-status]').forEach(x=>x.textContent=status)}catch{if(user||recovering)connectionBanner(true);else render()}finally{polling=false}},5000)}

 return {start,enqueue(){},status:()=>status};

})();
