from fastapi import FastAPI
from pydantic import BaseModel

# Création de l'application FastAPI
app = FastAPI(title="SentixAPI", description="BERT-based sentiment analysis REST API")

# Définition de la forme des données attendues en entrée (POST /predict)
class TextRequest(BaseModel):
    text: str

# Route de test, pour vérifier que l'API tourne
@app.get("/")
def root():
    return {"message": "SentixAPI is running"}

# Route principale (encore fictive à ce stade)
@app.post("/predict")
def predict(request: TextRequest):
    # Pour l'instant, réponse fixe, juste pour tester la structure
    return {
        "text": request.text,
        "sentiment": "positive",
        "confidence": 0.99
    }