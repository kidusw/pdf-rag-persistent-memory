from fastapi import Request

from app.config import Settings
from app.services import Services


def get_services(request: Request) -> Services:
    return request.app.state.services


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings
