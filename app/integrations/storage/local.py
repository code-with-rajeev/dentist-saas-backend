# Standard library
import os
import shutil
from datetime import datetime
from pathlib import Path

# Internal
from app.core.config import settings


class LocalStorageHandler:
    """
    Handles local filesystem storage for generated files (PDF reports).
    In production post-MVP, replace this with an S3-compatible handler.
    """

    def __init__(self) -> None:
        self.base_path = Path(settings.PDF_STORAGE_PATH)

    def _ensure_clinic_dir(self, clinic_id: str) -> Path:
        """Create clinic-specific subdirectory if it doesn't exist."""
        clinic_dir = self.base_path / clinic_id
        clinic_dir.mkdir(parents=True, exist_ok=True)
        return clinic_dir

    def save_pdf(self, clinic_id: str, filename: str, content: bytes) -> str:
        """
        Save PDF bytes to local storage.
        Returns the relative path string for storage in DB.
        """
        clinic_dir = self._ensure_clinic_dir(clinic_id)
        file_path = clinic_dir / filename
        file_path.write_bytes(content)
        return str(file_path)

    def get_pdf_path(self, file_path: str) -> Path:
        """Return a Path object for a stored file path."""
        return Path(file_path)

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists at the given path."""
        return Path(file_path).exists()

    def delete_file(self, file_path: str) -> None:
        """Delete a file if it exists."""
        path = Path(file_path)
        if path.exists():
            path.unlink()


local_storage = LocalStorageHandler()
