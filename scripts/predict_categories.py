import json
import re
from pathlib import Path
from transformers import pipeline
from langdetect import detect, DetectorFactory
from tqdm import tqdm

DetectorFactory.seed = 0  # stabilité langdetect

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
    if is_french:
        return text.lower()
    return normalize_arabic(text)

def preprocess_text(text):
    try:
        lang = detect(text)
        is_french = (lang == 'fr')
    except:
        is_french = False
    cleaned_text = clean_summary(text, is_french)
    if len(cleaned_text) < 20 or is_mostly_numeric_or_symbolic(cleaned_text):
        return None
    return cleaned_text[:1000]  # limite caractères pour éviter crash

# === Mapping label → nom et slug ===
category_mapping = {
    "Gestion de Sociétés": {
        "ar": "التصرف في شركات",
        "fr": "Gestion de Sociétés",
        "slug": "gestion_ste"
    },
    "Fonds de Commerce": {
        "ar": "اصول تجارية",
        "fr": "Fonds de Commerce",
        "slug": "fond_commerce"
    },
    "Associations, partis politiques et syndicats": {
        "ar": "جمعيات واحزاب ونقابات",
        "fr": "Associations, partis politiques et syndicats",
        "slug": "asso_pp_syndic"
    },
    "Actes judiciaires": {
        "ar": "اجراءات عدلية",
        "fr": "Actes judiciaires",
        "slug": "act_judciaire"
    },
    "Avis aux créanciers": {
        "ar": "اعلان للدائنين",
        "fr": "Avis aux créanciers",
        "slug": "avis_creanciers"
    },
    "Convocations": {
        "ar": "استدعاءات",
        "fr": "Convocations",
        "slug": "convocation"
    },
    "Divers": {
        "ar": "مختلفات",
        "fr": "Divers",
        "slug": "autre"
    }
}

# === Pipeline global pour éviter rechargement
classifier = None

def classify_categories(json_path: Path, model_dir: Path):
    global classifier
    if classifier is None:
        classifier = pipeline("text-classification", model=str(model_dir), tokenizer=str(model_dir))

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)  # Load the full JSON object
        articles = data.get("articles", [])  # Access the articles list

    for article in tqdm(articles, desc="📊 Prédiction des catégories"):
        if not article.get("is_legal", False):
            continue

        text = preprocess_text(article.get("articleText", ""))
        if not text:
            article["cat"] = []
            continue

        try:
            result = classifier(text, truncation=True, max_length=512)[0]
            label = result["label"]
            mapped = category_mapping.get(label, category_mapping["Divers"])

            article["cat"] = [{
                "slug": mapped["slug"],
                "name": {
                    "fr": mapped["fr"],
                    "ar": mapped["ar"]
                }
            }]

        except Exception as e:
            print(f"❌ Erreur pour article: {article.get('title', '')} → {e}")
            article["cat"] = []

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)  # Write back the full object

    print(f"\n✅ Fichier mis à jour avec champ 'cat' dans : {json_path}")