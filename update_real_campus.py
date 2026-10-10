from pathlib import Path
p=Path('D:/Hackathons/Genesis/amrita-entry/dist/app.js')
s=p.read_text(encoding='utf-8')
s=s.replace("hostel:'Anugraha'","hostel:'Gauthama Bhavanam'").replace("hostel:'Amritamayi'","hostel:'Mythreyi Bhavanam'")
marker="let viewFilter='all'"
s=s.replace(marker,"for(const v of visits){if(v.hostel==='Anugraha')v.hostel='Gauthama Bhavanam';else if(v.hostel==='Amritamayi')v.hostel='Mythreyi Bhavanam'}\n"+marker)
start=s.index('const routeSteps={')
end=s.index('function directions(id)',start)
s=s[:start]+"""const mappedHostels=['Gauthama Bhavanam','Mythreyi Bhavanam','Gargi Bhavanam','Agasthya Bhavanam','Vasishta Bhavanam','Yagnavalkya Bhavanam','Nachiketas Bhavanam','Vyasa Maharishi Bhavanam','Yagnavalkya Bhavanam Annexe','Adithi Bhavanam'];
function hostelSteps(hostel){return [['Main gate','Begin at the mapped main gate after security confirms entry.'],['Campus roads','Follow the highlighted road approach shown in the public map.'],['Hostel approach','Continue toward '+hostel+'. Confirm the permitted visitor route with security.'],['Arrival area','The route ends at the nearest mapped road. Ask staff for the exact hostel reception entrance.']]}
"""+s[end:]
s=s.replace('const steps=routeSteps[v.hostel];','const steps=mappedHostels.includes(v.hostel)?hostelSteps(v.hostel):null;')
s=s.replace("const left=v.hostel==='Anugraha';", "const left=v.hostel==='Gauthama Bhavanam';")
s=s.replace('Sample map for demonstration · This is not the actual campus layout. Ask security for the real route.','Amrita Vishwa Vidyapeetham, Coimbatore · Public-map preview. Buildings and roads use OpenStreetMap coordinates; heights and facades are illustrative. Confirm visitor routes and reception entrances with security.')
s=s.replace('Explore your route in 3D','Coimbatore campus in 3D').replace('Interactive campus preview','Ettimadai · Public map data').replace('3D CAMPUS <span>Sample layout</span>','AMRITA COIMBATORE <span>Georeferenced campus model</span>')
s=s.replace('Explore the buildings in 3D or play the route tour. This is a demonstration, not live location tracking.','Explore mapped buildings or play the approach-route tour. GPS requires your permission. Map data © OpenStreetMap contributors.')
s=s.replace('import(\'./campus3d.js\').then(({mountCampus})=>',"import('./campus-real.js').then(async ({mountCampus})=>")
s=s.replace('campusView=mountCampus(container,v.hostel);if(active)campusView.setStep(active)', 'const mounted=await mountCampus(container,v.hostel);if(mountVersion!==campusMountVersion){mounted.dispose();return}campusView=mounted;if(active)campusView.setStep(active)')
s=s.replace('Sample student directory: these names, hostel assignments, and wardens are for demonstration.','Sample student directory: student names and warden assignments are for demonstration. Hostel names are taken from the official Coimbatore directory.')
old='After your visit, meet the warden for exit clearance before returning to the main gate.</p></aside></div>'
new='''After your visit, meet the warden for exit clearance before returning to the main gate.</p><div class="campus-sources"><h3>Campus references</h3><a href="https://intranet.cb.amrita.edu/resources/hostel/FirstYear-Hostel-Warden-Contacts" target="_blank" rel="noopener">Official hostel contacts ↗</a><a href="https://intranet.cb.amrita.edu/2025/Gokulashtami/Campus_Road_Descriptions.pdf" target="_blank" rel="noopener">Official road map (2025) ↗</a><a href="https://www.amrita.edu/campus/coimbatore/tour/" target="_blank" rel="noopener">Official panoramic campus tour ↗</a><a href="https://www.openstreetmap.org/way/128964693" target="_blank" rel="noopener">OpenStreetMap campus data ↗</a><p class="hint">Student-to-hostel and warden assignments remain sample data.</p></div></aside></div>'''
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
# Update older regression checks for the verified hostel names.
t=Path('D:/Hackathons/Genesis/amrita-entry/check_lookup.cjs')
test=t.read_text().replace('Anugraha','Gauthama Bhavanam').replace('Amritamayi','Mythreyi Bhavanam').replace('/Sample map for demonstration/','/Public-map preview/')
t.write_text(test)
