from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Nom du modèle pré-entraîné qu'on va utiliser
MODEL_NAME = "nlptown/bert-base-multilingual-uncased-sentiment"

# Chargement du tokenizer et du modèle (ça télécharge le modèle la première fois, ~700 Mo)
print("Chargement du modèle... (peut prendre 1-2 minutes la première fois)")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

def predict_sentiment(text: str):
    # Étape 1-2 : texte -> tokens -> IDs numériques
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)

    # Étape 3-5 : passage dans BERT, sans calculer de gradients (on ne réentraîne pas)
    with torch.no_grad():
        outputs = model(**inputs)

    # outputs.logits contient les scores bruts (non normalisés) pour chaque classe
    logits = outputs.logits

    # On transforme les scores bruts en probabilités (qui somment à 1)
    probabilities = torch.nn.functional.softmax(logits, dim=1)

    # On récupère l'indice de la probabilité la plus élevée (0 à 4, car modèle 1-5 étoiles)
    predicted_class = torch.argmax(probabilities, dim=1).item()

    return predicted_class, probabilities

if __name__ == "__main__":
    text = "I love this movie, it was amazing!"
    predicted_class, probabilities = predict_sentiment(text)

    print(f"\nTexte : {text}")
    print(f"Classe prédite (0-4, 4 = très positif) : {predicted_class}")
    print(f"Probabilités : {probabilities}")