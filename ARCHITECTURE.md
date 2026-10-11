# AEMS — Simple System Architecture

```mermaid
flowchart TD
    Users[Parent / Guardian · Warden<br/>Guard · Security Head] --> Web[Web App<br/>Four role-based portals]
    Web <-->|Requests and results| API[FastAPI Backend]
    Camera[Laptop Camera] --> ANPR[Read Number Plate<br/>YOLO detector + OCR reader]
    ANPR -->|Plate number| API
    API <--> DB[(SQLite Database<br/>Visits · Approvals · Registered Vehicles<br/>Entry / Exit · Incidents · History)]
    API --> Check{Entry or Exit<br/>Permission Check}
    Check -->|Permission result| Guard[Guard verifies vehicle<br/>Inspection + People Count]
    Guard -->|Confirm passage| API
    API -->|Authorized facts| AI[Groq AI Assistant<br/>Questions + Daily Briefing]
    AI -->|Answer| Web

    classDef app fill:#FFF0F5,stroke:#BF0054,color:#263242;
    classDef data fill:#EAF5EF,stroke:#468A68,color:#263242;
    classDef ai fill:#FFF3DF,stroke:#D5A24D,color:#263242;
    class Users,Web,API,Check,Guard app;
    class DB data;
    class Camera,ANPR,AI ai;
```

The camera reads a vehicle number. The backend checks warden approvals or active registered-vehicle permission in the database. The guard verifies the vehicle, completes entry inspection, checks people counts and confirms passage. Visitor exit requires warden clearance and a matching entry/exit count. Recognition alone never opens the gate.

The AI assistant receives authorized aggregate facts for questions and daily briefings; it cannot approve vehicles or change records.
