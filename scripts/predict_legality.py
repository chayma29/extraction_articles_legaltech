# scripts/predict_legality.py
import json
import re
from pathlib import Path
from langdetect import detect
from transformers import pipeline
from tqdm import tqdm


def normalize_arabic(text):
    text = re.sub(r'[أإآٱ]', 'ا', text)
    text = re.sub(r'[\u064B-\u065F]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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


def classify_articles(json_path: Path, model_dir: Path):
    with json_path.open("r", encoding="utf-8") as f:
        articles = json.load(f)

    classifier = pipeline("text-classification", model=str(model_dir), tokenizer=str(model_dir))


    for article in tqdm(articles, desc="🔍 Classification des articles"):
        text = preprocess_text(article["articleText"])
        if not text:
            article["is_legal"] = False
            continue

        try:
            result = classifier(text, truncation=True)[0]
            label = result["label"]
            article["is_legal"] = label == "Positive"
        except Exception as e:
            print(f"❌ Erreur pour article: {article['title']} → {e}")
            article["is_legal"] = False

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)
    print(f"\n✅ Articles mis à jour avec le champ 'is_legal' dans : {json_path}")
