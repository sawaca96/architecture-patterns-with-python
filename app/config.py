from functools import lru_cache

from pydantic import BaseSettings


class Config(BaseSettings):
    PG_DSN: str


@lru_cache
def get_config() -> Config:
    return Config()
