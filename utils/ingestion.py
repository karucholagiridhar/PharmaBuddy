import os
from PIL import Image
import pypdf
from utils.utils import setup_logger

logger = setup_logger(__name__)

class IngestionManager:
    @staticmethod
    def load_file(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png']:
            return [Image.open(file_path)]
        elif ext == '.pdf':
            return file_path
        else:
            raise ValueError(f"Unsupported file type: {ext}")

