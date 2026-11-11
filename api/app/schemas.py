from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ApplianceType = Literal[
    "ac",
    "ceiling_fan",
    "pedestal_fan",
    "exhaust_fan",
    "air_cooler",
    "refrigerator",
    "deep_freezer",
    "microwave",
    "electric_oven",
    "water_dispenser",
    "electric_kettle",
    "washing_machine",
    "iron",
    "geyser",
    "water_pump",
    "tv",
    "desktop_pc",
    "laptop",
    "router",
    "ups",
    "led_bulb",
    "tube_light",
    "phone_charger",
    "vacuum_cleaner",
    "other",
]
SourceTag = Literal["label", "catalog", "guess", "user"]
ALLOWED_TYPES = set(ApplianceType.__args__)


class DetectedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ApplianceType
    brand: str | None = None
    model: str | None = None
    capacity_value: float | None = Field(default=None, ge=0)
    capacity_unit: str | None = None
    inverter: bool | None = None
    count: int = Field(default=1, ge=1, le=50)
    watts: float | None = Field(default=None, ge=0, le=20000)
    duty_factor: float = Field(default=1.0, gt=0, le=1)
    surge_factor: float = Field(default=1.0, ge=1)
    default_hours: float = Field(ge=0, le=24)
    confidence: float = Field(ge=0, le=1)
    source_tag: SourceTag
    label_text: str | None = None
    bbox: list[float] | None = None
    notes: str | None = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, value: list[float] | None) -> list[float] | None:
        if value is not None and (
            len(value) != 4 or any(coordinate < 0 or coordinate > 1 for coordinate in value)
        ):
            raise ValueError("bbox must contain four normalized coordinates in 0..1")
        return value


class HomeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="My home", min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    family_size: int | None = Field(default=None, ge=1, le=50)


class HomePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    family_size: int | None = Field(default=None, ge=1, le=50)


class HomeOut(HomeIn):
    id: str
    user_id: str
    system_kw: float | None = None
    created_at: str | None = None
    appliance_count: int = 0


class ApplianceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room: str | None = Field(default=None, max_length=80)
    type: ApplianceType
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    capacity_value: float | None = Field(default=None, ge=0)
    capacity_unit: str | None = Field(default=None, max_length=20)
    inverter: bool | None = None
    watts: float = Field(ge=0, le=20000)
    duty_factor: float = Field(default=1.0, gt=0, le=1)
    surge_factor: float = Field(default=1.0, ge=1)
    qty: int = Field(default=1, ge=1, le=50)
    hourly_use: list[float] = Field(default_factory=list)
    hours_per_day: float | None = Field(default=None, ge=0, le=24)
    is_essential: bool = False
    source_tag: SourceTag = "user"
    confidence: float | None = Field(default=None, ge=0, le=1)
    user_verified: bool = False
    image_path: str | None = None

    @field_validator("hourly_use")
    @classmethod
    def validate_hourly_use(cls, value: list[float]) -> list[float]:
        if value and len(value) != 24:
            raise ValueError("hourly_use must be empty or contain exactly 24 values")
        if any(hour < 0 or hour > 1 for hour in value):
            raise ValueError("hourly_use values must be between 0 and 1")
        return value


class AppliancePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room: str | None = Field(default=None, max_length=80)
    type: ApplianceType | None = None
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    capacity_value: float | None = Field(default=None, ge=0)
    capacity_unit: str | None = Field(default=None, max_length=20)
    inverter: bool | None = None
    watts: float | None = Field(default=None, ge=0, le=20000)
    duty_factor: float | None = Field(default=None, gt=0, le=1)
    surge_factor: float | None = Field(default=None, ge=1)
    qty: int | None = Field(default=None, ge=1, le=50)
    hourly_use: list[float] | None = None
    hours_per_day: float | None = Field(default=None, ge=0, le=24)
    is_essential: bool | None = None
    source_tag: SourceTag | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    user_verified: bool | None = None
    image_path: str | None = None

    @field_validator("hourly_use")
    @classmethod
    def validate_hourly_use(cls, value: list[float] | None) -> list[float] | None:
        if value is not None and len(value) != 24:
            raise ValueError("hourly_use must contain exactly 24 values")
        if value is not None and any(hour < 0 or hour > 1 for hour in value):
            raise ValueError("hourly_use values must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def validate_type(self) -> "AppliancePatch":
        if "type" in self.model_fields_set and self.type is None:
            raise ValueError("type cannot be null")
        return self


class ApplianceOut(BaseModel):
    id: str
    home_id: str
    room: str | None = None
    type: ApplianceType
    brand: str | None = None
    model: str | None = None
    capacity_value: float | None = None
    capacity_unit: str | None = None
    inverter: bool | None = None
    watts: float
    duty_factor: float
    surge_factor: float
    qty: int
    hourly_use: list[float]
    is_essential: bool
    source_tag: SourceTag
    confidence: float | None = None
    user_verified: bool
    image_path: str | None = None
    hours_per_day: float


class FinalizeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    final_items: list[DetectedItem] = Field(max_length=40)


class SizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assumptions: dict[str, float] | None = None


class SizeResponse(BaseModel):
    report_id: str
    created_at: str
    result: dict


class ReportSummary(BaseModel):
    id: str
    created_at: str
    daily_kwh: float
    peak_kw: float
    options: list[dict]
