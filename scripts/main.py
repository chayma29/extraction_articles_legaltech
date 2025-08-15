# C:\Users\chaym\Desktop\PFE\extraction_articles\scripts\main.py
from convert_pdf_to_images import convert_pdf_to_images
from segment_articles_with_yolo import segment_articles_with_yolo
from ocr_articles import apply_ocr_to_segmented_images
from detect_incomplet import detect_incomplete_articles
from associate_articles import associate_articles
from export_articles_to_json import export_articles_to_json
from predict_legality import classify_articles
from predict_categories import classify_categories
from merge_images import merge_images_in_folder
from clean_output import clean_png_files, collect_final_images
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

    # Vérifier s'il y a des articles_01 dans ocr_text
    article_01_files = list(output_text_dir.glob("*article_01_*.txt"))
    no_article_01 = len(article_01_files) == 0

    if not no_article_01:
        # Étape 4 : Détection des articles incomplets
        detect_incomplete_articles(output_dir)

        # Étape 5 : Association articles incomplets / article_01
        associate_articles(output_dir)
        
        # Étape 5.5 : Fusionner les images dans 'complete_articles'
        complete_articles_dir = output_dir / "complete_articles"
        merged_images_dir = complete_articles_dir / "merged_images"
        if complete_articles_dir.exists():
            merge_images_in_folder(complete_articles_dir, merged_images_dir)
        else:
            print("Dossier 'complete_articles' non trouvé, fusion des images ignorée.")

        
    else:
        print("Aucun article_01 détecté, on saute la détection d'incomplets et l'association.")

    # Étape 6 : Nettoyer et collecter les images finales
    clean_png_files(output_dir)
    collect_final_images(output_dir)
    
    # Étape 7 : Export JSON
    final_json = output_dir / "articles_final.json"

    export_articles_to_json(
        complete_dir=output_dir / "complete_articles",  # peut ne pas exister, la fonction gère
        ocr_dir=output_text_dir,
        incomplets_dir=output_dir / "incomplets",       # peut ne pas exister, la fonction gère
        output_json_path=final_json
    )


    # Étape 8 : Classification légalité
    classify_articles(
        json_path=final_json,
        model_dir=Path("../models/legal_classifier_roberta_ADA")
    )
    # Étape 9 : Classification catégories
    classify_categories(
        json_path=final_json,

        model_dir=Path("../models/roberta_multiclass_classifier")
    )
    