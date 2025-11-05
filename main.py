import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from database import create_document, get_documents

app = FastAPI(title="KisanMitr Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "KisanMitr API running"}

# ---- AI Plant Doctor (Mock) ----
class Diagnosis(BaseModel):
    disease: str
    severity: str
    organic_treatment: str
    chemical_treatment: str

@app.post("/ai/diagnose", response_model=Diagnosis)
async def diagnose(image: UploadFile = File(...)):
    name = (image.filename or "").lower()
    if any(k in name for k in ["blight", "tomato"]):
        disease = "Early blight"
        severity = "moderate"
        organic = "Remove affected leaves, apply neem oil 0.5% every 7 days, improve airflow."
        chemical = "Spray chlorothalonil or mancozeb at label rates; rotate actives."
    elif any(k in name for k in ["rust", "wheat"]):
        disease = "Wheat rust"
        severity = "high"
        organic = "Plant resistant varieties, remove volunteer hosts, compost teas weekly."
        chemical = "Triazole fungicide (e.g., propiconazole) per label; monitor spread."
    else:
        disease = "Leaf spot"
        severity = "low"
        organic = "Neem + soap spray 1x/week; avoid overhead irrigation."
        chemical = "Copper-based fungicide if spread increases."
    return Diagnosis(
        disease=disease,
        severity=severity,
        organic_treatment=organic,
        chemical_treatment=chemical,
    )

# ---- Chatbot (Simple heuristic) ----
class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1)

class ChatResponse(BaseModel):
    reply: str

@app.post("/chat", response_model=ChatResponse)
def chat(msg: ChatMessage):
    text = msg.message.lower()
    if any(w in text for w in ["pest", "insect", "worm"]):
        reply = "For pests, start with yellow sticky traps and neem oil; escalate to targeted pesticides if thresholds are exceeded."
    elif any(w in text for w in ["fertilizer", "npk", "nitrogen", "phosphorus", "potassium"]):
        reply = "Base fertilizer on soil test. Typical basal NPK 10-26-26 for crops needing early P, split nitrogen into 2-3 applications."
    elif any(w in text for w in ["irrigation", "water", "drip"]):
        reply = "Prefer drip irrigation early morning. Maintain soil moisture at field capacity; mulch to reduce evaporation."
    else:
        reply = "Share crop, stage, and issue. I’ll suggest region-appropriate best practices."
    return ChatResponse(reply=reply)

# ---- Calendar (Mongo-backed) ----
class CalendarEvent(BaseModel):
    title: str
    date: datetime
    category: str = Field(description="spray | fertilizer | irrigation | harvest | other")
    notes: Optional[str] = None

@app.post("/calendar/events")
def create_event(event: CalendarEvent):
    event_id = create_document("calendarevent", event)
    return {"id": event_id}

@app.get("/calendar/events")
def list_events(limit: int = 50):
    items = get_documents("calendarevent", {}, limit)
    # Convert datetimes to isoformat manually for safety
    for it in items:
        if isinstance(it.get("date"), datetime):
            it["date"] = it["date"].isoformat()
        if "_id" in it:
            it["id"] = str(it.pop("_id"))
    return {"items": items}

# ---- Health/Test ----
@app.get("/test")
def test_database():
    response = {
        "backend": "running",
        "database_url": bool(os.getenv("DATABASE_URL")),
        "database_name": bool(os.getenv("DATABASE_NAME")),
    }
    try:
        from database import db
        response["db_connected"] = db is not None
    except Exception:
        response["db_connected"] = False
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
