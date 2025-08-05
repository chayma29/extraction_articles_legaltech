import json
import re
from pathlib import Path
from transformers import pipeline
from langdetect import detect
from tqdm import tqdm


# === Normalisation pour l'arabe ===
def normalize_arabic(text):
    text = re.sub(r'[أإآٱ]', 'ا', text)
    text = re.sub(r'[\u064B-\u065F]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# === Nettoyage général ===
def is_mostly_numeric_or_symbolic(text):
    cleaned = re.sub(r'\s+', '', text)
    if not cleaned:
        return True
    non_alpha = sum(1 for c in cleaned if not (c.isalpha() or c in ' .,-/'))
    return non_alpha / len(cleaned) > 0.8

def clean_summary(text, is_french=False):
    text = re.sub(r'[|*+()\[\]{}:;]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower() if is_french else normalize_arabic(text)

def preprocess_text(text):
    try:
        lang = detect(text)
        is_french = lang == 'fr'
    except:
        is_french = False
    cleaned_text = clean_summary(text, is_french)
    if len(cleaned_text) < 20 or is_mostly_numeric_or_symbolic(cleaned_text):
        return None
    return cleaned_text


# === Mapping ID → catégorie arabe/français
category_names = {
    "Actes judiciaires": "اجراءات عدلية / Actes judiciaires",
    "Fonds de Commerce": "اصول تجارية / Fonds de Commerce",
    "Convocations": "استدعاءات / Convocations",
    "Avis aux créanciers": "اعلان للدائنين / Avis aux créanciers",
    "Gestion de Sociétés": "التصرف في شركات / Gestion de Sociétés",
    "Associations, Partis, Syndicats et Syndics": "جمعيات واحزاب ونقابات / Associations, Partis, Syndicats et Syndics",
    "Divers": "مختلفات / Divers"
}


# === Prédiction des catégories
def classify_categories(json_path: Path, model_dir: Path):
    with json_path.open("r", encoding="utf-8") as f:
        articles = json.load(f)

    classifier = pipeline("text-classification", model=str(model_dir), tokenizer=str(model_dir))

    for article in tqdm(articles, desc="📊 Prédiction des catégories"):
        if not article.get("is_legal", False):
            continue

        text = preprocess_text(article["articleText"])
        if not text:
            article["categories"] = []
            continue

        try:
            result = classifier(text, truncation=True)[0]
            label = result["label"]
            label_name = category_names.get(label, "مختلفات / Divers")  

            # Séparation arabe / français
            if " / " in label_name:
                arabic, french = label_name.split(" / ", 1)
            else:
                arabic, french = label_name, label

            article["categories"] = [arabic.strip(), french.strip()]

        except Exception as e:
            print(f"❌ Erreur pour article: {article['title']} → {e}")
            article["categories"] = []

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Fichier mis à jour avec catégories dans : {json_path}")
