from app.core.config.settings import settings


def is_development() -> bool:
    return settings.environment == "development"


def is_production() -> bool:
    return settings.environment == "production"


def is_testing() -> bool:
    return settings.environment == "testing"
