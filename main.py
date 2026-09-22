from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# --- Configuration du modèle ---
MODEL_NAME = "nlptown/bert-base-multilingual-uncased-sentiment"

# --- Chargement du modèle UNE SEULE FOIS, au démarrage du serveur ---
print("Chargement du modèle BERT...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
print("Modèle chargé avec succès.")

# --- Mapping des classes 0-4 vers des labels lisibles ---
# Le modèle donne une note de 1 à 5 étoiles (indices 0 à 4)
LABELS = {
    0: "negative",   # 1 étoile
    1: "negative",   # 2 étoiles
    2: "neutral",    # 3 étoiles
    3: "positive",   # 4 étoiles
    4: "positive",   # 5 étoiles
}

# --- Application FastAPI ---
app = FastAPI(title="SentixAPI", description="BERT-based sentiment analysis REST API")

class TextRequest(BaseModel):
    text: str

@app.get("/")
def root():
    return {"message": "SentixAPI is running"}

@app.post("/predict")
def predict(request: TextRequest):
    text = request.text.strip()

    # --- Gestion d'erreur : texte vide ---
    if not text:
        raise HTTPException(status_code=400, detail="Le champ 'text' ne peut pas être vide.")

    # --- Gestion d'erreur : texte trop long (BERT limite à 512 tokens) ---
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Le texte est trop long (max ~2000 caractères).")

    try:
        # Tokenization + passage dans le modèle
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)

        with torch.no_grad():
            outputs = model(**inputs)

        logits = outputs.logits
        probabilities = torch.nn.functional.softmax(logits, dim=1)[0]
        predicted_class = torch.argmax(probabilities).item()
        confidence = probabilities[predicted_class].item()

        return {
            "text": text,
            "sentiment": LABELS[predicted_class],
            "confidence": round(confidence, 4),
            "star_rating": predicted_class + 1  # 1 à 5 étoiles
        }

    except Exception as e:
        # --- Gestion d'erreur : tout ce qui pourrait planter côté modèle ---
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prédiction : {str(e)}")