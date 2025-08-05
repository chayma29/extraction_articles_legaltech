import json
from pathlib import Path
import re
from langdetect import detect
from datetime import datetime

def extract_reference_from_last_line(content):
    last_line = content.strip().split('\n')[-1]
    matches = re.findall(r'\b(?:\$?[A-Z]?[0-9]{4,}[A-Z0-9]*|[0-9]{4,}[A-Z]{1,})\b', last_line)
    return matches[0] if matches else None

def detect_lang_from_folder(folder_name):
    if "- ar -" in folder_name:
        return "ar"
    elif "- fr -" in folder_name:
        return "fr"
    else:
        return "unknown"

def extract_date_from_folder(folder_name):
    match = re.search(r"\d{4}-\d{2}-\d{2}", folder_name)
    return match.group(0) if match else "1900-01-01"

def extract_page_from_filename(filename):
    match = re.search(r'_page_(\d+)', filename)
    return int(match.group(1)) if match else None

def export_articles_to_json(complete_dir: Path, ocr_dir: Path, incomplets_dir: Path, segment_dir: Path, output_json_path: Path):
    all_articles = []

    folder_name = complete_dir.parent.name
    journal_name = folder_name.split(" - ")[0].strip()
    lang = detect_lang_from_folder(folder_name)
    date_str = extract_date_from_folder(folder_name)

    print(f"\n=== Export JSON pour: {journal_name} ({lang}) - {date_str} ===\n")

    # === 1. Articles COMPLETS
    for file_path in sorted(complete_dir.rglob("*.txt")):
        try:
            with file_path.open('r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                print(f"🔸 Ignoré (vide): {file_path.name}")
                continue

            reference = extract_reference_from_last_line(content)
            page = extract_page_from_filename(file_path.name)
            file_field = [str(p) for p in sorted(file_path.parent.glob("*.png"))]

            if not file_field:
                print(f"⚠️ Aucune image trouvée pour: {file_path.name}")
                continue

            article_data = {
                "doc_id": date_str,
                "title": f"{journal_name} - {lang} - {date_str}" + (f" - {reference}" if reference else ""),
                "reference": reference,
                "lang": lang,
                "articleText": content,
                "publishedAt": f"{date_str}T00:00:00+00:00",
                "file": file_field,
                "source": journal_name,
                "source_grps": ["ANNONCES"],
                "categories": [],
                "page": page,
                "extras": None
            }
            all_articles.append(article_data)
            print(f"✅ Article COMPLET ajouté : {file_path.name}")

        except Exception as e:
            print(f"❌ Erreur complete_article: {file_path.name} : {e}")

    # === 2. Liste des incomplets
    incomplets_files = set(f.name for f in incomplets_dir.glob("*article_00_*.txt"))

    # === 3. OCR restants
    for file_path in sorted(ocr_dir.glob("*.txt")):
        filename = file_path.name
        filename_stem = file_path.stem

        if "article_complet" in filename or "article_01" in filename:
            continue

        is_article_00 = "article_00" in filename
        is_incomplet = filename in incomplets_files

        if is_article_00 and is_incomplet:
            print(f"🔸 Ignoré : {filename} est un article_00 incomplet.")
            continue

        try:
            with file_path.open('r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                print(f"🔸 Ignoré OCR vide : {filename}")
                continue

            reference = extract_reference_from_last_line(content)
            if not reference:
                print(f"🔸 Ignoré OCR sans référence : {filename}")
                continue

            # 📌 Recherche image dans ocr_dir d'abord
            image_path = ocr_dir / (filename_stem + ".png")
            if not image_path.exists():
                # 📌 Sinon dans segment_dir
                image_path = segment_dir / (filename_stem + ".png")
                if not image_path.exists():
                    print(f"🔸 Ignoré OCR sans image trouvée : {filename}")
                    continue

            page = extract_page_from_filename(filename)

            article_data = {
                "doc_id": date_str,
                "title": f"{journal_name} - {lang} - {date_str}" + (f" - {reference}" if reference else ""),
                "reference": reference,
                "lang": lang,
                "articleText": content,
                "publishedAt": f"{date_str}T00:00:00+00:00",
                "file": str(image_path),
                "source": journal_name,
                "source_grps": ["ANNONCES"],
                "categories": [],
                "page": page,
                "extras": None
            }

            all_articles.append(article_data)
            print(f"✅ Article OCR ajouté : {filename}")

        except Exception as e:
            print(f"❌ Erreur OCR : {filename} : {e}")

    # === Sauvegarde JSON
    print(f"\n🔹 TOTAL articles exportés : {len(all_articles)}\n")
    with output_json_path.open('w', encoding='utf-8') as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=4)
    print(f"📦 Fichier JSON créé : {output_json_path}")
