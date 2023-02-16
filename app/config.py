from pydantic import BaseSettings


class Config(BaseSettings):
    PG_DSN: str
    REDIS_DSN: str


config = Config()
