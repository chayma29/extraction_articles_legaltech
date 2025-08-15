from pathlib import Path
from PIL import Image

def merge_images_in_folder(folder_path: Path, output_folder: Path):
    output_folder.mkdir(parents=True, exist_ok=True)

    for subfolder in folder_path.iterdir():
        if not subfolder.is_dir() or not subfolder.name.startswith("article_complet_"):
            continue

        # Trouver article_00 et article_01
        article_00 = next((p for p in subfolder.glob("*article_00*.png")), None)
        article_01 = next((p for p in subfolder.glob("*article_01*.png")), None)

        if not article_00 or not article_01:
            print(f"⚠️ Pas assez d'images dans {subfolder} pour fusionner")
            continue

        # Charger dans l'ordre
        images_paths = [article_00, article_01]
        images = [Image.open(p) for p in images_paths]

        max_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)

        merged_img = Image.new("RGB", (max_width, total_height), (255, 255, 255))
        y_offset = 0
        for img in images:
            merged_img.paste(img, (0, y_offset))
            y_offset += img.height

        # 🔹 Chercher un fichier .txt dans le même dossier
        txt_file = next(subfolder.glob("*.txt"), None)
        if txt_file:
            output_filename = txt_file.stem + ".png"
        else:
            # Fallback : nom basé sur article_00
            output_filename = article_00.stem + ".png"

        output_path = output_folder / output_filename
        merged_img.save(output_path)

        print(f"✅ Fusion créée : {output_path}")
