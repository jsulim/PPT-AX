from pydantic import BaseModel


class ComponentHealth(BaseModel):
    ok: bool
    detail: str


class HealthResponse(BaseModel):
    status: str
    components: dict[str, ComponentHealth]


class FontHealth(BaseModel):
    status: str
    worker: ComponentHealth
    fonts: list[str]
