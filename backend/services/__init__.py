"""
Services module for model serving and data lookup.
Supports both absolute and package-relative imports.
"""
try:
    from backend.services.model_service import ModelService
    from backend.services.data_service import DataService
except ImportError:
    from services.model_service import ModelService
    from services.data_service import DataService

__all__ = ["ModelService", "DataService"]
