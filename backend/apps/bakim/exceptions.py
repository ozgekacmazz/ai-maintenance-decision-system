from rest_framework.exceptions import ValidationError


class BakimDogrulamaHatasi(ValidationError):
    """Bakım iş kurallarının güvenli 400 yanıtına çevrilmesini sağlar."""
