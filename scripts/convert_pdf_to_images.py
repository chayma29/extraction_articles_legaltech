from pdf2image import convert_from_path
from utils import ensure_dir
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def convert_pdf_to_images(pdf_path: str, nom_journal: str, output_root: str = "output", config=None) -> str:
    """Convert PDF to images and return output directory."""
    if config is None:
        import yaml
        with open("../config/config.yaml", "r") as f:
            config = yaml.safe_load(f)

    date_du_jour = datetime.today().strftime("%Y-%m-%d")

    # ✅ Nouvelle structure : output/nom_journal/date_du_jour
    output_dir = Path(output_root) / nom_journal / date_du_jour
    ensure_dir(output_dir)

    if not Path(pdf_path).exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return None

    logger.info(f"Converting PDF: {pdf_path}")
    try:
        images = convert_from_path(pdf_path, dpi=int(config.get("dpi", 200)))
        for page_num, image in enumerate(images, 1):
            image_filename = f"{nom_journal}_page_{page_num}.png"
            image_path = output_dir / image_filename
            image.save(image_path, "PNG")
            logger.info(f"Saved page {page_num}/{len(images)}: {image_path}")
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        return None

    logger.info(f"Conversion completed: {output_dir}")
    return str(output_dir)
