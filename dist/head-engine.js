(function(root){
 'use strict';
 const day=t=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(t));
 const hour=t=>Number(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',hour:'2-digit',hourCycle:'h23'}).format(new Date(t)));
 const shift=(date,n)=>new Date(Date.parse(date+'T12:00:00Z')+n*86400000).toISOString().slice(0,10);
 function fixtures(now=new Date()){
  const visits=[],logs=[],end=day(now);let serial=0;
  for(let d=14;d>=0;d--){const date=shift(end,-d);for(let j=0;j<12+(d%5);j++){
   const h=[8,9,10,10,11,12,14,15,16,17,19,22][j%12],id='SAMPLE-'+String(++serial).padStart(4,'0');
   const entered=new Date(date+'T'+String(h).padStart(2,'0')+':'+String((j*7)%60).padStart(2,'0')+':00+05:30').toISOString();
   if(Date.parse(entered)>+now)continue;
   const duration=j===10?420:60+(j%4)*35,exitTime=new Date(Date.parse(entered)+duration*60000).toISOString(),exited=Date.parse(exitTime)<=+now?exitTime:null;
   const v={id,visitor:['Sample parent A','Sample guardian B','Sample visitor C'][j%3],relation:j%3===1?'Guardian':'Parent',plate:'TN38DM'+String(1000+serial),student:'Sample student '+(j%3+1),studentId:'SAMPLE-ID-'+(j%3+1),branch:['Computer Science','ECE','AI'][j%3],hostel:['Gauthama Bhavanam','Mythreyi Bhavanam','Gargi Bhavanam'][j%3],warden:'Sample warden',vehicleType:j%4===0||j===11?'Van':'Car',date,status:exited?'completed':'inside',created:new Date(Date.parse(entered)-3600000).toISOString(),entered,exited,purpose:'Sample family visit',inspectionSeconds:120+(j%4)*20};
   visits.push(v);logs.push({visit:id,plate:v.plate,action:'Entry approved',actor:'Sample warden',time:v.created},{visit:id,plate:v.plate,action:'Vehicle entered',actor:'Sample guard',time:entered});if(exited)logs.push({visit:id,plate:v.plate,action:'Vehicle departed',actor:'Sample guard',time:exited});
  }}return{visits,logs:logs.sort((a,b)=>b.time.localeCompare(a.time))};
 }
 function parse(text,now=new Date()){
  let q=text.trim().toLowerCase(),f={},recognized=false;
  if(!q)return{filters:f};
  if(/\btoday\b/.test(q)){f.from=f.to=day(now);recognized=true;q=q.replace(/\btoday\b/g,'')}
  if(/\byesterday\b/.test(q)){f.from=f.to=shift(day(now),-1);recognized=true;q=q.replace(/\byesterday\b/g,'')}
  const weekday=q.match(/\blast (sunday|monday|tuesday|wednesday|thursday|friday|saturday)\b/);
  if(weekday){const index=['sunday','monday','tuesday','wednesday','thursday','friday','saturday'].indexOf(weekday[1]),current=new Date(day(now)+'T12:00:00Z').getUTCDay();f.from=f.to=shift(day(now),-((current-index+7)%7||7));recognized=true;q=q.replace(weekday[0],'')}
  const dates=q.match(/\d{4}-\d{2}-\d{2}/g);if(dates){f.from=dates[0];f.to=dates[1]||dates[0];recognized=true;q=q.replace(/\d{4}-\d{2}-\d{2}/g,'')}
  for(const [word,start,end] of [['night',18,6],['morning',6,12],['afternoon',12,18],['evening',18,22]])if(new RegExp('\\b'+word+'\\b').test(q)){f.startHour=start;f.endHour=end;recognized=true;q=q.replace(new RegExp('\\b'+word+'\\b','g'),'')}
  const types=q.match(/\b(vans?|cars?|bikes?|buses?)\b/);if(types){f.vehicleType=types[0].startsWith('van')?'Van':types[0].startsWith('car')?'Car':types[0].startsWith('bike')?'Bike':'Bus';q=q.replace(types[0],'');recognized=true}
  const status=q.match(/\b(completed|pending|approved|inside|rejected|exit)\b/);if(status){f.status=status[0];q=q.replace(status[0],'');recognized=true}
  const plate=q.match(/\b[a-z]{2}\s?\d{2}\s?[a-z]{1,3}\s?\d{4}\b/i);if(plate){f.text=plate[0].replace(/\s/g,'').toUpperCase();q=q.replace(plate[0],'');recognized=true}
  q=q.replace(/\b(show|find|me|all|visitor|visitors|vehicle|vehicles|visits|logs|entries|on|from|to|at|during|the|and|with|please)\b/g,'').replace(/[.,?]/g,'').trim();
  if(q||!recognized)return{error:'Use dates, time of day, status, or vehicle type. For names and hostel names, use the history text filter. Unrecognized text: '+(q||text)};
  return{filters:f};
 }
 function filter(rows,f){return rows.filter(v=>{const time=v.entered||v.created,date=time?day(time):v.date,h=time?hour(time):null;
  if(f.from&&date<f.from||f.to&&date>f.to)return false;
  const status=['pending','approved'].includes(v.status)&&v.date<day(new Date())?'expired':v.status;
  if(f.status&&status!==f.status||f.vehicleType&&v.vehicleType!==f.vehicleType)return false;
  if(f.startHour!=null&&f.endHour!=null&&(h===null||(f.startHour<f.endHour?!(h>=f.startHour&&h<f.endHour):!(h>=f.startHour||h<f.endHour))))return false;
  return !f.text||[v.id,v.visitor,v.plate,v.student,v.studentId,v.hostel,v.warden,v.branch].join(' ').toLowerCase().includes(f.text.toLowerCase());
 })}
 function anomalies(rows,now=new Date(),limit=240){const result=[];for(const v of rows){if(!v.entered)continue;const h=hour(v.entered),minutes=(Date.parse(v.exited||now)-Date.parse(v.entered))/60000;if(h<6||h>=21)result.push({id:v.id+':hours',visit:v.id,plate:v.plate,title:'Outside normal review hours',detail:'Entry at '+String(h).padStart(2,'0')+':'+new Date(v.entered).toLocaleTimeString('en-GB',{timeZone:'Asia/Kolkata',minute:'2-digit'})+' IST; review window is 06:00–21:00.',time:v.entered});if(minutes>limit)result.push({id:v.id+':dwell',visit:v.id,plate:v.plate,title:'Long visit duration',detail:Math.round(minutes)+' minutes '+(v.exited?'before exit':'inside')+'; threshold '+limit+' minutes.',time:v.exited||v.entered});}return result.sort((a,b)=>b.time.localeCompare(a.time))}
 function forecast(rows,now=new Date()){const end=day(now),dates=[...new Set(rows.filter(v=>v.entered&&day(v.entered)<end&&day(v.entered)>=shift(end,-14)).map(v=>day(v.entered)))].sort();if(dates.length<3)return{days:dates.length,bars:[],message:'Need at least 3 dates with entry records. Missing dates are not assumed to have zero traffic.'};const counts=Array(24).fill(0);rows.forEach(v=>{if(v.entered&&dates.includes(day(v.entered)))counts[hour(v.entered)]++});return{days:dates.length,bars:counts.map((count,h)=>({hour:h,value:count/dates.length})),message:'Hourly mean over '+dates.length+' recorded dates in the last 14 days. Estimate, not a trained ML model.'}}
 function queue(waiting,lanes,seconds){return{waitMinutes:Math.ceil(waiting/lanes)*seconds/60,capacity:Math.floor(3600/seconds)*lanes,suggest:waiting/lanes>=4}}
 function facts(rows,logs,date,alerts){const entries=rows.filter(v=>v.entered&&day(v.entered)===date),departures=rows.filter(v=>v.exited&&day(v.exited)===date),events=logs.filter(l=>day(l.time)===date);return[
  {id:'entries',text:entries.length+' vehicle entries recorded on '+date+'.'},
  {id:'departures',text:departures.length+' vehicle departures recorded on '+date+'.'},
  {id:'inside',text:rows.filter(v=>v.entered&&!v.exited).length+' visits currently marked inside in this dataset.'},
  {id:'events',text:events.length+' audit events recorded on '+date+'.'},
  {id:'alerts',text:alerts.filter(a=>day(a.time)===date).length+' rule flags associated with '+date+'; flags need human review.'}
 ]}
 const api={day,hour,shift,fixtures,parse,filter,anomalies,forecast,queue,facts};if(typeof module!=='undefined')module.exports=api;else root.HeadEngine=api;
})(typeof window!=='undefined'?window:globalThis);
