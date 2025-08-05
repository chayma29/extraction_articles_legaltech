import logging
import re
from pathlib import Path
import csv
import torch
from transformers import BertTokenizer, BertForNextSentencePrediction
from collections import defaultdict
import unicodedata
from langdetect import detect, DetectorFactory
from utils import ensure_dir  
import shutil

# Pour assurer stabilité détection langue
DetectorFactory.seed = 0

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Charger BERT NSP
tokenizer = BertTokenizer.from_pretrained('bert-base-multilingual-cased')
model = BertForNextSentencePrediction.from_pretrained('bert-base-multilingual-cased')
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'[|*+()\[\]{}:;]+', ' ', text)
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'[^\w\s.,;!?-\u0600-\u06FF\u0750-\u077F]', '', text)
    return text

def load_text(file_path: Path) -> tuple:
    try:
        with file_path.open('r', encoding='utf-8') as f:
            text = f.read().strip()
            lang = detect(text) if text else 'unknown'
            text = clean_text(text)
            return text, lang
    except Exception as e:
        logger.error(f"Erreur lecture {file_path.name} : {e}")
        return "", "unknown"

def get_nsp_score(text1: str, text2: str) -> float:
    if not text1 or not text2:
        return 0.0
    try:
        inputs = tokenizer(text1, text2, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)
            return probs[0][0].item()  # probabilité que text2 suit text1
    except Exception as e:
        logger.error(f"Erreur calcul NSP: {e}")
        return 0.0

def find_best_matches(incomplets: list, candidates: list, max_chars=1000):
    results = []
    used_candidates = set()
    processed_incomplets = set()

    incomplete_data = [(p, t[:max_chars]) for p, t, _ in incomplets]
    candidate_data = [(p, load_text(p)[0][:max_chars]) for p in candidates]

    similarities = defaultdict(dict)
    for inc_path, inc_text in incomplete_data:
        for cand_path, cand_text in candidate_data:
            if not inc_text or not cand_text:
                continue
            sim = get_nsp_score(inc_text, cand_text)
            similarities[inc_path][cand_path] = sim
            logger.info(f"Sim {inc_path.name} <> {cand_path.name}: {sim:.4f}")

    for _ in range(min(len(incomplete_data), len(candidates))):
        max_sim = -1
        best_pair = None
        for inc_path in similarities:
            if inc_path in processed_incomplets:
                continue
            for cand_path, sim in similarities[inc_path].items():
                if cand_path in used_candidates:
                    continue
                if sim > max_sim:
                    max_sim = sim
                    best_pair = (inc_path, cand_path)
        if best_pair:
            inc_path, cand_path = best_pair
            results.append({
                "article_00": inc_path.name,
                "article_01": cand_path.name,
                "similarity": f"{max_sim:.4f}",
                "status": "Matched"
            })
            used_candidates.add(cand_path)
            processed_incomplets.add(inc_path)
            similarities.pop(inc_path, None)
        else:
            break

    # Tous les incomplets non appariés sont unmatched
    for inc_path, _, _ in incomplets:
        if inc_path not in processed_incomplets:
            results.append({
                "article_00": inc_path.name,
                "article_01": None,
                "similarity": None,
                "status": "Unmatched"
            })

    return results


def combine_articles(inc_path: Path, cand_path: Path, output_dir: Path, page_num: str, article_idx: str):
    try:
        inc_text, _ = load_text(inc_path)
        cand_text, _ = load_text(cand_path)

        logger.info(f"Article incomplet ({inc_path.name}) longueur: {len(inc_text)}")
        logger.info(f"Article candidat   ({cand_path.name}) longueur: {len(cand_text)}")

        combined = inc_text.strip() + "\n\n" + cand_text.strip()

        # Créer dossier spécifique
        article_folder = output_dir / f"article_complet_{article_idx}"
        ensure_dir(article_folder)

        # Sauvegarder texte combiné
        combined_txt_path = article_folder / f"{inc_path.stem.replace('article_00', 'article_complet')}.txt"
        with combined_txt_path.open('w', encoding='utf-8') as f:
            f.write(combined)

        # === Chemin correct vers segment depuis base_folder
        base_folder = output_dir.parent  # -> JrSahafa - ar - 2025-08-04
        segment_dir = base_folder / "segment"

        # Récupération des noms originaux pour les images
        img_00_name = inc_path.with_suffix(".png").name
        img_01_name = cand_path.with_suffix(".png").name

        img_00_path = segment_dir / img_00_name
        img_01_path = segment_dir / img_01_name

        if img_00_path.exists():
            shutil.copy(img_00_path, article_folder / img_00_name)
        else:
            logger.warning(f"Image manquante : {img_00_path}")

        if img_01_path.exists():
            shutil.copy(img_01_path, article_folder / img_01_name)
        else:
            logger.warning(f"Image manquante : {img_01_path}")

        logger.info(f"Article combiné et images copiées dans: {article_folder}")

    except Exception as e:
        logger.error(f"Erreur combinaison {inc_path.name} + {cand_path.name} : {e}")



def get_page_number(filename: str) -> str:
    m = re.search(r'_page_(\d+)_', filename)
    return m.group(1).zfill(3) if m else "000"

def associate_articles(base_folder: Path):
    logger.info(f"Démarrage association dans {base_folder}")

    ocr_dir = base_folder / "ocr_text"
    incomplets_dir = base_folder / "incomplets"
    output_dir = base_folder / "complete_articles"
    assoc_dir = base_folder / "associations"

    if not ocr_dir.exists() or not incomplets_dir.exists():
        logger.error(f"ocr_text ou incomplets absent dans {base_folder}")
        return

    # Liste des articles incomplets (article_00) à traiter
    incomplets_list = list(incomplets_dir.glob("*article_00_*.txt"))
    logger.info(f"{len(incomplets_list)} articles incomplets trouvés.")

    # Liste des candidats article_01 dans ocr_text
    candidates_list = list(ocr_dir.glob("*article_01_*.txt"))
    logger.info(f"{len(candidates_list)} articles_01 candidats trouvés.")

    # Charger textes incomplets (avec langue ignorée ici)
    incomplets_texts = []
    for f in incomplets_list:
        txt, lang = load_text(f)
        incomplets_texts.append((f, txt, lang))

    # Trouver meilleurs appariements
    matches = find_best_matches(incomplets_texts, candidates_list)

    # Assurer dossiers de sortie
    ensure_dir(output_dir)
    ensure_dir(assoc_dir)

    # Combiner articles appariés et créer rapport CSV
    rows = []
    for m in matches:
        page_num = get_page_number(m["article_00"])
        article_idx_match = re.search(r"_article_00_(\d+)\.txt$", m["article_00"])
        article_idx = article_idx_match.group(1) if article_idx_match else "0"

        if m["status"] == "Matched" and m["article_01"]:
            inc_path = incomplets_dir / m["article_00"]
            cand_path = ocr_dir / m["article_01"]
            combine_articles(inc_path, cand_path, output_dir, page_num, article_idx)

        rows.append({
            "page": page_num,
            "article_00": m["article_00"],
            "article_01": m["article_01"],
            "similarity": m["similarity"],
            "status": m["status"]
        })

    # Écriture rapport CSV
    csv_path = assoc_dir / "association_report.csv"
    with csv_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["page", "article_00", "article_01", "similarity", "status"])
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Association terminée. Rapport: {csv_path}")
    logger.info(f"Articles combinés dans: {output_dir}")
