# C:\Users\chaym\Desktop\PFE\extraction_articles\scripts\main.py
from convert_pdf_to_images import convert_pdf_to_images
from segment_articles_with_yolo import segment_articles_with_yolo
from ocr_articles import apply_ocr_to_segmented_images
from detect_incomplet import detect_incomplete_articles
from associate_articles import associate_articles
from export_articles_to_json import export_articles_to_json
from predict_legality import classify_articles
from predict_categories import classify_categories
from pathlib import Path
import yaml

if __name__ == "__main__":
    # === Configuration utilisateur ===
    with open("../config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    pdf_path = config["pdf_path"]
    nom_journal = config["nom_journal"]
    model_path = config["model_path"]
    output_root = config["output_root"]

    
    # Étape 1 : Convertir PDF en images
    output_dir = convert_pdf_to_images(pdf_path, nom_journal, output_root)
    if output_dir is None:
        print(f"Échec lors de la conversion du PDF {pdf_path}. Vérifiez le fichier ou les dépendances.")
        exit(1)
    output_dir = Path(output_dir)  # Convert to Path only if successful

    # Étape 2 : Passer les images sur YOLOv8
    segment_articles_with_yolo(output_dir, model_path, config.get("yolo_batch_size", 10))

    # Étape 3 : Segments → OCR
    segment_dir = output_dir / "segment"
    output_text_dir = output_dir / "ocr_text"
    apply_ocr_to_segmented_images(segment_dir, output_text_dir, config.get("ocr_language_hints", ["ar", "fr"]))

    #  Étape 4 : Détection des articles incomplets
    detect_incomplete_articles(output_dir)

    # ÉTAPE 5 : Association des articles incomplets avec article_01 
    associate_articles(output_dir)

    # ÉTAPE 6 : Export JSON des articles OCR et complets
    final_json = output_dir / "articles_final.json"

    export_articles_to_json(
    complete_dir=output_dir / "complete_articles",
    ocr_dir=output_dir / "ocr_text",
    incomplets_dir=output_dir / "incomplets",
    segment_dir=output_dir / "segment",
    output_json_path=final_json
    )

    # Étape 7 : Prédire si chaque article est légal ou non
    classify_articles(
        json_path=final_json,
        model_dir=Path("../models/legal_classifier_roberta_ADA")
    )

# Étape 8 : Prédire les catégories des articles légaux
classify_categories(
    json_path=final_json,
    model_dir=Path("../models/roberta_multiclass_classifier")
)