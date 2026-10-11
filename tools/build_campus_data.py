from pathlib import Path
import xml.etree.ElementTree as ET
import json,math,heapq
root=Path(__file__).resolve().parents[1]
r=ET.parse(root/'tools/campus-osm.xml').getroot()
nodes={n.get('id'):{'lat':float(n.get('lat')),'lon':float(n.get('lon')),'tags':{t.get('k'):t.get('v') for t in n.findall('tag')}} for n in r.findall('node')}
ways={w.get('id'):{'id':w.get('id'),'nodes':[n.get('ref') for n in w.findall('nd') if n.get('ref') in nodes],'tags':{t.get('k'):t.get('v') for t in w.findall('tag')}} for w in r.findall('way')}
gate=nodes['988441542'];lat,lon=gate['lat'],gate['lon'];scale=.2
def xy(i):
 n=nodes[i];return [round((n['lon']-lon)*111320*math.cos(math.radians(lat))*scale,3),round(-(n['lat']-lat)*111320*scale,3)]
boundary=[xy(i) for i in ways['128964693']['nodes']]
def inside(x,z):
 hit=False
 for (a,b),(c,d) in zip(boundary,boundary[1:]+boundary[:1]):
  if (b>z)!=(d>z) and x<(c-a)*(z-b)/(d-b)+a:hit=not hit
 return hit
buildings=[];roads=[];areas=[]
for w in ways.values():
 p=[xy(i) for i in w['nodes']]
 if len(p)<2:continue
 t=w['tags'];cx=sum(v[0] for v in p)/len(p);cz=sum(v[1] for v in p)/len(p)
 if not (inside(cx,cz) or any(inside(*v) for v in p)):continue
 if 'building' in t:buildings.append({'id':w['id'],'points':p,'name':t.get('name',''),'levels':int(t.get('building:levels','3')) if t.get('building:levels','3').isdigit() else 3,'estimatedHeight':'height' not in t,'kind':t.get('tourism',t.get('amenity','building'))})
 if 'highway' in t and t['highway'] not in ['construction','proposed']:roads.append({'id':w['id'],'points':p,'nodes':w['nodes'],'kind':t['highway'],'name':t.get('name',''),'access':t.get('access','unknown')})
 if t.get('leisure') in ['pitch','swimming_pool','garden','playground'] or t.get('landuse')=='grass':areas.append({'points':p,'kind':t.get('leisure','grass'),'name':t.get('name','')})
graph={}
for road in roads:
 for a,b in zip(road['nodes'],road['nodes'][1:]):
  pa,pb=xy(a),xy(b);distance=math.dist(pa,pb);graph.setdefault(a,[]).append((b,distance));graph.setdefault(b,[]).append((a,distance))
start=min(graph,key=lambda i:math.dist(xy(i),[0,0]))
def route(building):
 center=[sum(p[0] for p in building['points'])/len(building['points']),sum(p[1] for p in building['points'])/len(building['points'])]
 end=min(graph,key=lambda i:math.dist(xy(i),center));q=[(0,start)];dist={start:0};prev={}
 while q:
  d,u=heapq.heappop(q)
  if d!=dist[u]:continue
  if u==end:break
  for v,c in graph[u]:
   if d+c<dist.get(v,float('inf')):dist[v]=d+c;prev[v]=u;heapq.heappush(q,(d+c,v))
 if end not in dist:return None
 ids=[end]
 while ids[-1]!=start:ids.append(prev[ids[-1]])
 return {'points':[xy(i) for i in ids[::-1]],'distanceMetres':round(dist[end]/scale),'destinationCenter':center,'lastRoadGapMetres':round(math.dist(xy(end),center)/scale),'status':'public-map preview; visitor access and reception entrance unverified'}
routes={}
for b in buildings:
 if b['kind']=='hostel':
  name='Mythreyi Bhavanam' if b['name']=='Maitheyi Bhavanam' else b['name'];b['name']=name;routes[name]=route(b)
landmarks=[{'name':n['tags']['name'],'point':xy(i)} for i,n in nodes.items() if n['tags'].get('name') and inside(*xy(i)) and n['tags'].get('name') in ['Natarajar statue','Arjuna Statue','Saraswati Statue','University Clinic','Temple']]
data={'name':'Amrita Vishwa Vidyapeetham, Coimbatore','origin':{'latitude':lat,'longitude':lon},'metresToWorld':scale,'boundary':boundary,'buildings':buildings,'roads':roads,'areas':areas,'landmarks':landmarks,'routes':routes,'attribution':'Â© OpenStreetMap contributors, ODbL','source':'https://www.openstreetmap.org/way/128964693','retrieved':'2026-10-10','limitations':'Footprints and roads from OSM. Heights and facade details are illustrative. Visitor access and exact hostel reception entrances need on-site confirmation.'}
(root/'dist/campus-data.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('Bounds',min(p[0] for p in boundary),max(p[0] for p in boundary),min(p[1] for p in boundary),max(p[1] for p in boundary))
print('Origin',data['origin'],'Buildings',len(buildings),'Roads',len(roads),'Routes',list(routes))
