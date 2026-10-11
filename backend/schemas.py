import re
from datetime import date as Date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Login(Input):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)
    portal: Literal['security','head','warden','admin','registry'] | None = None
    warden_id: Literal['MENON','DEVI'] = 'MENON'

class VisitCreate(Input):
    visitor: str = Field(min_length=2, max_length=100)
    phone: str = Field(pattern=r'^\d{10}$')
    relation: Literal['Parent','Guardian','Other visitor']
    plate: str = Field(min_length=6, max_length=20)
    studentId: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=2, max_length=180)
    date: Date
    vehicleType: Literal['Car','Van','Bike','Bus','Other'] = 'Car'
    @field_validator('plate')
    @classmethod
    def normalize(cls, value):
        value = re.sub(r'[\s.-]', '', value.upper())
        if not re.fullmatch(r'[A-Z0-9]{6,16}', value): raise ValueError('Invalid plate')
        return value

class Change(Input):
    version: int = Field(ge=1)
    note: str = Field(default='', max_length=500)

class ApprovalChange(Change):
    decision: Literal['approve','reject'] = 'approve'
    meeting_verified: bool = False

class InspectionChange(Change):
    passed: bool

class Passage(Change):
    person_count: int = Field(ge=1, le=100, strict=True)
    visitor_verified: bool
    plate: str = Field(min_length=6, max_length=20)
    gate_id: str = 'MAIN'
    original_plate: str = Field(default='', max_length=30)

class IncidentCreate(Input):
    visit_id: str
    title: str = Field(min_length=3, max_length=120)
    owner: Literal['security','warden']
    priority: Literal['Normal','High'] = 'Normal'
    note: str = Field(min_length=3, max_length=500)

class IncidentChange(Change):
    action: Literal['investigate','resolve']
    outcome: str = Field(min_length=2, max_length=150)

class SettingsChange(Input):
    waiting: int = Field(ge=0, le=1000)
    lanes: int = Field(ge=1, le=10)
    seconds: int = Field(ge=10, le=1800)
    dwell: int = Field(ge=30, le=10080)

class AIMessage(Input):
    role: Literal['user','assistant']
    content: str = Field(min_length=1, max_length=2000)
class Chat(Input):
    messages: list[AIMessage] = Field(min_length=1, max_length=10)
    model: str = 'openai/gpt-oss-20b'
    context: dict | None = None
class Summary(Input):
    date: Date | None = None
    model: str = 'openai/gpt-oss-20b'
    facts: list[dict] | None = None
