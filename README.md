# Amrita University Entry Monitoring System

Static hackathon prototype styled after the supplied Amrita student portal reference.

Run `python -m http.server 4173 --directory dist` from this directory and open http://localhost:4173.

Three interfaces: visitor requests and status tracking; warden entry and exit approvals; security plate correction, approval lookup, entry/exit records and audit history.

Sample flow: scan TN38AB1234 in Security, verify and record entry, approve its exit in Warden after checking the verification box, then scan at the exit gate and record departure. KL07CD5678 starts with entry approval pending.

Data lives in localStorage in the same browser/origin. All names and assignments are fictional demo records. This prototype does not include real ANPR, role authentication, a shared backend, university student records, camera snapshots, or physical gate control. Production use needs these integrations and verified institutional approval rules. Never use real visitor personal data in this demo.
