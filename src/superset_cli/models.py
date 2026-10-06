from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, field_validator


_HTTP_URL = TypeAdapter(AnyHttpUrl)


class JWTSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username_env: str
    password_env: str
    provider: Literal["db", "ldap"] = "db"


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["cookie", "jwt"] = "cookie"
    jwt: JWTSettings | None = None


class InstanceConfig(BaseModel):
    name: str
    base_url: str
    auth: AuthConfig | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return str(_HTTP_URL.validate_python(value)).rstrip("/")


class Config(BaseModel):
    model_config = ConfigDict(frozen=True)

    instances: list[InstanceConfig] = Field(default_factory=list)
    default_instance: str | None = None
