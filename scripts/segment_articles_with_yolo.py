from ultralytics import YOLO
import cv2
from pathlib import Path
from utils import ensure_dir
import logging

logger = logging.getLogger(__name__)

def segment_articles_with_yolo(image_dir: str, model_path: str, batch_size: int = 10):
    image_dir = Path(image_dir)
    output_segment_dir = ensure_dir(image_dir / "segment")

    if not Path(model_path).exists():
        logger.error(f"YOLO model not found: {model_path}")
        return

    model = YOLO(model_path)
    image_files = [f for f in image_dir.glob("*.png")]
    if not image_files:
        logger.error(f"No PNG images found in {image_dir}")
        return

    logger.info(f"Processing {len(image_files)} images")
    for i in range(0, len(image_files), batch_size):
        batch = image_files[i:i + batch_size]
        for file in batch:
            image = cv2.imread(str(file))
            if image is None:
                logger.error(f"Failed to load image: {file}")
                continue

            results = model(image)
            if not results or not results[0].boxes:
                logger.warning(f"No detections for {file}")
                continue

            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            classes = results[0].boxes.cls.cpu().numpy().astype(int)

            for idx, ((x1, y1, x2, y2), cls) in enumerate(zip(boxes, classes)):
                segment = image[y1:y2, x1:x2]
                class_label = f"article_{cls:02d}"
                segment_filename = f"{file.stem}_{class_label}_{idx+1}.png"
                segment_path = output_segment_dir / segment_filename
                cv2.imwrite(str(segment_path), segment)
                logger.info(f"Saved segment: {segment_filename}")

    logger.info(f"Segmentation completed: {output_segment_dir}")