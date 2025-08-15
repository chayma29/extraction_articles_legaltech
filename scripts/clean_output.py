import shutil
from pathlib import Path

def clean_png_files(root_path: Path):
    """Supprime seulement les PNG directement dans root_path (pas les sous-dossiers)."""
    for png_file in root_path.glob("*.png"):  # pas de rglob ici
        try:
            png_file.unlink()
        except Exception as e:
            print(f"Impossible de supprimer {png_file} : {e}")

def collect_final_images(output_dir):
    output_dir = Path(output_dir)
    segment_dir = output_dir / "segment"
    merged_dir = output_dir / "complete_articles" / "merged_images"
    incomplets_dir = output_dir / "incomplets"

    # Cas 1 : dossier "incomplets" n'existe pas
    if not incomplets_dir.exists():
        print("[INFO] Dossier 'incomplets' introuvable → Copie de toutes les images du segment.")
        for img_path in segment_dir.glob("*.png"):
            shutil.copy(img_path, output_dir)
        return

    # Cas 2 : dossier "incomplets" existe → traitement normal
    print("[INFO] Dossier 'incomplets' trouvé → Application du traitement complet.")

    # Charger les noms des fichiers txt incomplets
    incomplets_txt = set(f.name for f in incomplets_dir.glob("*.txt"))

    # 1) Images de complete_articles/merged_images avec "article_complet"
    for img_path in merged_dir.glob("*.png"):
        shutil.copy(img_path, output_dir)

    # 2) Images "article_00" dont le txt n’est pas dans incomplets
    for img_path in segment_dir.glob("*article_00*.png"):
        txt_name = img_path.with_suffix(".txt").name
        if txt_name not in incomplets_txt:
            shutil.copy(img_path, output_dir)