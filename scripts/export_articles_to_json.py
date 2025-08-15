import json
import time
from pathlib import Path
import re

def detect_reference(article_text: str) -> str:
    """Détecte la référence si elle existe."""
    lines = [line.strip() for line in article_text.strip().split("\n") if line.strip()]
    if not lines:
        return "Pas de référence trouvée"

    last_line = lines[-1]
    last_line_clean = re.sub(r"\s+", " ", last_line)

    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}\s+[A-Za-zéûôâîç]+\s+\d{4}\b",
        r"\b\d{1,2}\s+[ء-ي]+\s+\d{4}\b"
    ]
    for pattern in date_patterns:
        if re.search(pattern, last_line_clean):
            return "Pas de référence trouvée"

    ref_pattern = r"^[\$A-Za-z0-9\u0621-\u064A:/\\\-\_,\. ]{2,}$"
    if re.match(ref_pattern, last_line_clean) and len(last_line_clean.split()) <= 4:
        return last_line_clean.strip()

    return "Pas de référence trouvée"

def detect_lang_from_folder(folder_path: Path) -> str:
    """Détermine la langue selon le nom du journal."""
    journaux_ar = {"JrChourouk", "JrAssabeh", "JrSahafa"}
    nom_journal = folder_path.name
    return "ar" if nom_journal in journaux_ar else "fr"

def extract_date_from_folder(folder_path: Path) -> str:
    """Extrait la date depuis un chemin output/nom_journal/YYYY-MM-DD."""
    date_str = folder_path.name
    return date_str if re.match(r"\d{4}-\d{2}-\d{2}", date_str) else "1900-01-01"

def extract_page_from_filename(filename: str):
    """Extrait le numéro de page depuis le nom du fichier."""
    match = re.search(r'_page_(\d+)', filename)
    return match.group(1) if match else None

def export_articles_to_json(complete_dir: Path, ocr_dir: Path, incomplets_dir: Path, output_json_path: Path):
    """Exporte les articles selon la présence ou non d'articles incomplets."""
    date_folder = complete_dir.parent
    nom_journal = date_folder.parent.name
    date_str = extract_date_from_folder(date_folder)
    langue = detect_lang_from_folder(Path(nom_journal))

    # Dossier parent des images PNG
    images_dir = date_folder

    articles = []

    # Vérifier présence article_01
    has_article_01 = any(ocr_dir.glob("*article_01_*.txt"))

    # Liste des articles incomplets
    incomplets_files = set()
    if incomplets_dir.exists():
        incomplets_files = {f.name for f in incomplets_dir.glob("*article_00_*.txt")}

    def add_article(txt_path: Path):
        """Ajoute un article au tableau final."""
        content = txt_path.read_text(encoding="utf-8").strip()
        if not content:
            return

        reference = detect_reference(content)
        page = extract_page_from_filename(txt_path.name)
        image_name = txt_path.stem + ".png"  # même nom que le txt
        image_path = images_dir / image_name

        articles.append({
            "title": f"{nom_journal} - {langue} - {date_str} - {reference}",
            "reference": reference,
            "lang": langue,
            "articleText": content,
            "date": "-".join(reversed(date_str.split("-"))),
            "file": str(image_path),
            "source": nom_journal,
            "source_grps": ["ANNONCES"],
            "cat": {},
            "page": str(page) if page else None,
            "extras": None
        })

    if not has_article_01:
        # Cas simple : tous les txt de ocr_text
        for txt_path in ocr_dir.glob("*.txt"):
            add_article(txt_path)
    else:
        # 1. Articles article_00 qui ne sont pas incomplets
        for txt_path in ocr_dir.glob("*article_00_*.txt"):
            if txt_path.name not in incomplets_files:
                add_article(txt_path)

        # 2. Articles complets fusionnés
        for subdir in complete_dir.glob("article_complet_*"):
            if subdir.is_dir():
                for txt_path in subdir.glob("*.txt"):
                    add_article(txt_path)

    # Structure finale
    output_data = {
        "doc_id": date_str,
        "doc_type": nom_journal,
        "creation_date": int(time.time()),
        "articles": articles
    }

    # Sauvegarde JSON
    output_json_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=4), encoding="utf-8")
    print(f"✅ JSON généré : {output_json_path} ({len(articles)} articles)")
