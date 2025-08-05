from pathlib import Path
import re
from utils import ensure_dir
import shutil

def looks_like_date(s: str) -> bool:
    date_patterns = [
        r'\b\d{4}/\d{2}/\d{2}\b',
        r'\b\d{2}[-/]\d{2}[-/]\d{4}\b',
        r'\b\d{4}-\d{2}-\d{2}\b'
    ]
    return any(re.search(p, s) for p in date_patterns)

def has_reference_raw(file_path: Path) -> bool:
    try:
        with file_path.open('r', encoding='utf-8') as f:
            lines = f.read().strip().splitlines()
            if not lines:
                return False

            last_lines = lines[-2:]
            ref_pattern = re.compile(r'\b(?:\$?[A-Z]?[0-9]{4,}[A-Z0-9]*|[0-9]{4,}[A-Z]{1,})\b', re.IGNORECASE)

            for line in last_lines:
                if looks_like_date(line):
                    continue
                if ref_pattern.search(line):
                    return True
            return False
    except Exception as e:
        print(f"Erreur lecture fichier {file_path.name} : {e}")
        return False

def detect_incomplete_articles(output_dir: Path):
    ocr_dir = output_dir / "ocr_text"
    if not ocr_dir.exists():
        print(f"Dossier OCR introuvable : {ocr_dir}")
        return

    files = list(ocr_dir.glob("**/*article_00_*.txt"))
    if not files:
        print("Aucun fichier article_00 trouvé.")
        return

    incomplete_dir = ensure_dir(output_dir / "incomplets")
    print(f"\nAnalyse de {len(files)} fichiers dans : {ocr_dir}\n")

    for f in sorted(files):
        if not has_reference_raw(f):
            print(f" Incomplet : {f.name}")
            shutil.copy(f, incomplete_dir / f.name)
        else:
            print(f" Complet   : {f.name}")

    print(f"\n Articles incomplets copiés dans : {incomplete_dir}")
