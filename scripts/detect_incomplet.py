from pathlib import Path
import re
import shutil
from utils import ensure_dir


def detect_reference(article_text: str) -> str:
    """Détecte et retourne la référence si présente, sinon 'Pas de référence trouvée'."""
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


def has_reference(file_path: Path) -> bool:
    """Vérifie si un fichier contient une référence valide."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return detect_reference(content) != "Pas de référence trouvée"
    except Exception as e:
        print(f"Erreur lecture fichier {file_path.name} : {e}")
        return False


def detect_incomplete_articles(output_dir: Path):
    """Détecte et copie les articles incomplets dans un dossier 'incomplets'.
       Supposé être appelé uniquement si des article_01 existent."""
    
    ocr_dir = output_dir / "ocr_text"
    if not ocr_dir.exists():
        print(f"Dossier OCR introuvable : {ocr_dir}")
        return

    files_00 = list(ocr_dir.glob("**/*article_00_*.txt"))
    if not files_00:
        print("Aucun fichier article_00 trouvé.")
        return

    incomplete_dir = ensure_dir(output_dir / "incomplets")
    print(f"\nAnalyse de {len(files_00)} fichiers dans : {ocr_dir}\n")

    for f in sorted(files_00):
        if not has_reference(f):
            print(f"🔸 Incomplet : {f.name}")
            shutil.copy(f, incomplete_dir / f.name)
        else:
            print(f"✅ Complet   : {f.name}")

    print(f"\n📂 Articles incomplets copiés dans : {incomplete_dir}")
