PDF Article Extraction Pipeline

Pipeline d'extraction et classification d'articles de journaux tunisiens à partir de PDF.

Installation
============
pip install -r requirements.txt

Prérequis système :
- Poppler : sudo apt-get install poppler-utils (Ubuntu) ou brew install poppler (macOS)
- Google Cloud Vision API avec credentials JSON

Configuration
=============
Modifier config/config.yaml :

pdf_path: "/path/to/file.pdf"
nom_journal: "JrSahafa"
model_path: "/path/to/yolo/model.pt"
google_credentials: "/path/to/credentials.json"

Utilisation
===========
cd scripts
python main.py

Sortie
======
Articles extraits et classifiés dans output/journal/date/articles_final.json

Format :
{
  "articles": [{
    "title": "Journal - langue - date - référence",
    "articleText": "texte...",
    "is_legal": true,
    "cat": [{"slug": "gestion_ste", "name": {"fr": "...", "ar": "..."}}]
  }]
}

Pipeline
========
1. PDF → Images
2. YOLO → Segmentation articles  
3. OCR → Extraction texte
4. Association articles incomplets
5. Classification IA (légalité + catégories)
6. Export JSON