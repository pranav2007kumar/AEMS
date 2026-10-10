# Coimbatore campus model: sources and limits

Retrieved 10 October 2026 for the localhost prototype.

- Public geometry: https://www.openstreetmap.org/way/128964693 . XML downloaded from the OpenStreetMap map API and processed into `dist/campus-data.json`. Contains 99 building footprints, 61 road/path features, selected landscaped areas and named landmarks. Main gate node 988441542 is the projection origin: 10.8992656 N, 76.9006082 E. World coordinates are 0.2 units per metre. Data © OpenStreetMap contributors, licensed under ODbL: https://www.openstreetmap.org/copyright . The extracted dataset is provided locally, with its attribution.
- Official road layout: https://intranet.cb.amrita.edu/2025/Gokulashtami/Campus_Road_Descriptions.pdf . Downloaded as `campus-roads-2025.pdf`; its second page was inspected for landmarks and road relationships.
- Official hostel names and public phone contacts: https://intranet.cb.amrita.edu/resources/hostel/FirstYear-Hostel-Warden-Contacts . Used for the 14-entry contact directory. This is a list of entries, not an assertion about the number of currently operational hostels.
- Official infrastructure: https://webfiles.amrita.edu/2024/05/infrastructure-coimbatore.pdf . Lists academic buildings, hostel names and facilities. Newer report discovered: https://webfiles.amrita.edu/2026/03/infrastructure-cbr.pdf . These inventory tables are not georeferenced building surveys.
- Official panoramic tour: https://www.amrita.edu/campus/coimbatore/tour/ . Linked for the user; panorama media is not reproduced.
- Historical visitor information: https://intranet.cb.amrita.edu/guidelines-for-visit-by-parents-and-students . This is explicitly for the 2020/2021 admission cohorts and contains pandemic-era rules; it is not used as current gate policy.

## Model limits

Horizontal footprints/road geometry and geographic projection come from public OSM data. Building heights, facade/window design, trees and gate architecture are illustrative. Missing buildings or reception entrances are not invented. Routes are graph-based approaches along mapped roads/paths ending at the road nearest a mapped hostel; they are not campus-approved vehicle routes. No route is supplied for an unlocated hostel. The data may be incomplete or out of date.

GPS uses the browser's permission-based `watchPosition`, projects the fix into the public model, and shows an accuracy circle. Follow is enabled after a fix inside the mapped campus polygon; no coordinates are transmitted to a remote map service. Outside-campus or denied/unavailable location states are displayed. The watch is cleared when leaving the view. Device GPS accuracy and real on-campus travel still need testing.

Real student records and current student-to-hostel/warden assignments are not publicly available here. The student directory remains fictional demonstration data. The interface labels it accordingly.
