from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, field_validator


_HTTP_URL = TypeAdapter(AnyHttpUrl)


class InstanceConfig(BaseModel):
    name: str
    base_url: str

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return str(_HTTP_URL.validate_python(value)).rstrip("/")


class Config(BaseModel):
    model_config = ConfigDict(frozen=True)

    instances: list[InstanceConfig] = Field(default_factory=list)
