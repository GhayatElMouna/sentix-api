from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

from posts_store import find_comment, get_post, normalize_url, record_analysis

MODEL_NAME = "nlptown/bert-base-multilingual-uncased-sentiment"
STATIC_DIR = Path(__file__).parent / "static"
MAX_TEXT_LEN = 2000
MAX_BATCH = 200

tokenizer = None
model = None


def get_model():
    global tokenizer, model
    if model is None:
        print("Chargement du modèle BERT...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        print("Modèle chargé avec succès.")
    return tokenizer, model

LABELS = {
    0: "negative",
    1: "negative",
    2: "neutral",
    3: "positive",
    4: "positive",
}

app = FastAPI(title="SentixAPI", description="Analyse de sentiment des commentaires réseaux sociaux")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextRequest(BaseModel):
    text: str


class BatchRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    platform: str | None = None


class PostCommentRequest(BaseModel):
    url: str
    text: str


def classify(text: str) -> dict:
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Le champ 'text' ne peut pas être vide.")
    if len(cleaned) > MAX_TEXT_LEN:
        raise HTTPException(status_code=400, detail="Le texte est trop long (max ~2000 caractères).")

    try:
        tok, mdl = get_model()
        inputs = tok(
            cleaned,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512,
        )
        with torch.no_grad():
            outputs = mdl(**inputs)

        probabilities = torch.nn.functional.softmax(outputs.logits, dim=1)[0]
        predicted_class = int(torch.argmax(probabilities).item())
        confidence = float(probabilities[predicted_class].item())
        return {
            "text": cleaned,
            "sentiment": LABELS[predicted_class],
            "confidence": round(confidence, 4),
            "star_rating": predicted_class + 1,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prédiction : {str(e)}")


@app.get("/health")
def health():
    return {"message": "SentixAPI is running"}


@app.post("/predict")
def predict(request: TextRequest):
    return classify(request.text)


@app.post("/predict/batch")
def predict_batch(request: BatchRequest):
    comments = [t.strip() for t in request.texts if t and t.strip()]
    if not comments:
        raise HTTPException(status_code=400, detail="Aucun commentaire à analyser.")
    if len(comments) > MAX_BATCH:
        raise HTTPException(
            status_code=400,
            detail=f"Trop de commentaires (max {MAX_BATCH}).",
        )

    results = []
    for comment in comments:
        if len(comment) > MAX_TEXT_LEN:
            results.append(
                {
                    "text": comment[:120] + "…",
                    "sentiment": "skipped",
                    "confidence": 0,
                    "star_rating": None,
                    "error": "Texte trop long",
                }
            )
            continue
        results.append(classify(comment))

    counted = [r for r in results if r.get("sentiment") in {"positive", "neutral", "negative"}]
    total = len(counted) or 1
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for item in counted:
        counts[item["sentiment"]] += 1

    return {
        "platform": request.platform,
        "total": len(counted),
        "skipped": len(results) - len(counted),
        "counts": counts,
        "percentages": {
            "positive": round(counts["positive"] * 100 / total, 1),
            "neutral": round(counts["neutral"] * 100 / total, 1),
            "negative": round(counts["negative"] * 100 / total, 1),
        },
        "results": results,
    }


@app.get("/posts")
def read_post(url: str = Query(..., min_length=1)):
    normalized = normalize_url(url)
    if not normalized:
        raise HTTPException(status_code=400, detail="Le lien du post est requis.")
    return get_post(normalized)


@app.post("/posts/analyze")
def analyze_post_comment(request: PostCommentRequest):
    normalized = normalize_url(request.url)
    if not normalized:
        raise HTTPException(status_code=400, detail="Le lien du post est requis.")

    existing = find_comment(normalized, request.text)
    if existing:
        result = {
            "text": existing["text"],
            "sentiment": existing["sentiment"],
            "confidence": existing["confidence"],
            "star_rating": existing["star_rating"],
        }
        return {"duplicate": True, "result": result, "post": existing["post"]}

    result = classify(request.text)
    return record_analysis(normalized, result)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def frontend():
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return {"message": "SentixAPI is running"}
    return FileResponse(index)
