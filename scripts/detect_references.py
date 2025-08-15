import re

def detect_reference(article_text):
    # Séparer en lignes et garder la dernière ligne non vide
    lines = [line.strip() for line in article_text.strip().split("\n") if line.strip()]
    if not lines:
        return "Pas de référence trouvée"

    last_line = lines[-1]

    # Nettoyer espaces multiples mais garder les symboles ($, //, etc.)
    last_line_clean = re.sub(r"\s+", " ", last_line)

    # Exclure si c'est une date
    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",          # formats numériques
        r"\b\d{1,2}\s+[A-Za-zéûôâîç]+\s+\d{4}\b",      # format français
        r"\b\d{1,2}\s+[ء-ي]+\s+\d{4}\b"                # format arabe
    ]
    for pattern in date_patterns:
        if re.search(pattern, last_line_clean):
            return "Pas de référence trouvée"

    # Regex pour détecter une référence : inclut le symbole $
    ref_pattern = r"^[\$A-Za-z0-9\u0621-\u064A:/\\\-\_,\. ]{2,}$"

    # Pas de phrases longues → max 4 "mots"
    if re.match(ref_pattern, last_line_clean) and len(last_line_clean.split()) <= 4:
        return last_line_clean.strip()  # garder tel quel (avec $)

    return "Pas de référence trouvée"


def detect_reference_from_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return detect_reference(content)
    except FileNotFoundError:
        return "Fichier introuvable"
    except Exception as e:
        return f"Erreur lors de la lecture : {e}"


# ==== TEST AVEC UN FICHIER ====
path = r"C:\Users\chaym\Desktop\PFE\extraction_articles\output\JrSahafa - ar - 2025-08-05\ocr_text\JrSahafa_page_18_article_01_13.txt"
print(detect_reference_from_file(path))
