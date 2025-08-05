# src/ocr_articles.py
import os
import yaml
from google.cloud import vision
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Load configuration
with open("../config/config.yaml", "r") as f: 
    config = yaml.safe_load(f)

# Set Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config["google_credentials"]

# Initialize Google Cloud Vision client
client = vision.ImageAnnotatorClient()

def extract_text_from_image(image_path: Path, language_hints: list = None) -> str:
    """Extract text from an image using Google Cloud Vision."""
    if language_hints is None:
        language_hints = config.get("ocr_language_hints", ["ar", "fr"])
    try:
        with image_path.open("rb") as img:
            content = img.read()
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image, image_context={"language_hints": language_hints})
        if response.error.message:
            logger.error(f"Vision API error for {image_path}: {response.error.message}")
            return ""
        return response.full_text_annotation.text
    except Exception as e:
        logger.error(f"OCR failed for {image_path}: {e}")
        return ""

def apply_ocr_to_segmented_images(segment_dir: Path, output_text_dir: Path, language_hints: list = None):
    """Apply OCR to all images in segment_dir and save results."""
    from utils import ensure_dir
    output_text_dir = ensure_dir(output_text_dir)
    image_files = list(segment_dir.glob("*.png"))

    def process_image(image_file):
        logger.info(f"Processing OCR for {image_file.name}")
        text = extract_text_from_image(image_file, language_hints)
        if text.strip():
            output_file = output_text_dir / f"{image_file.stem}.txt"
            with output_file.open("w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"Saved OCR result: {output_file}")
        else:
            logger.warning(f"No text extracted from {image_file.name}")

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(process_image, image_files)

    logger.info(f"OCR completed: {output_text_dir}")