"""Shared API schema primitives.

* :class:`ApiModel` — base for every response/request model. Money fields are serialised
  as JSON strings (``"480000.00"``), quantised to the minor units of the sibling
  ``currency`` field when one exists (``usd_*`` fields are USD).
* :data:`Money` — ``Decimal`` annotated for string serialisation and an OpenAPI ``string``.
* :class:`Page` — the list envelope ``{items, page, page_size, total}``.
* :class:`ProblemDetails` — the problem+json error body.
"""

from __future__ import annotations

import types
import typing
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any, ClassVar, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    WithJsonSchema,
    model_serializer,
)

from app.domain.money.currency import minor_units_or_none

SortOrder = Literal["asc", "desc"]
JSONDict = dict[str, Any]

USD_CURRENCY_SOURCE = "__USD__"


class _MoneyMarker:
    """Annotation marker identifying money fields for currency-aware serialisation."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "MONEY"


MONEY_MARKER = _MoneyMarker()


def format_money(value: Decimal, minor_units: int | None = None) -> str:
    """Render a Decimal as a plain amount string.

    With ``minor_units`` the amount is quantised half-up to exactly that many decimals
    (``JPY`` → ``"1500000"``). Without it, trailing zeros beyond two decimals are dropped
    and at least two decimals are kept (``Decimal("480000.0000")`` → ``"480000.00"``).
    """
    if not value.is_finite():
        raise ValueError("Money amounts must be finite")
    if minor_units is not None:
        return format(value.quantize(Decimal(1).scaleb(-minor_units), rounding=ROUND_HALF_UP), "f")
    text = format(value, "f")
    whole, dot, fraction = text.partition(".")
    if not dot:
        return f"{whole}.00"
    fraction = fraction.rstrip("0")
    if len(fraction) < 2:
        fraction = fraction.ljust(2, "0")
    return f"{whole}.{fraction}"


def _serialize_money_default(value: Decimal) -> str:
    return format_money(value)


Money = Annotated[
    Decimal,
    MONEY_MARKER,
    PlainSerializer(_serialize_money_default, return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "format": "decimal",
            "pattern": r"^-?\d+(\.\d+)?$",
            "examples": ["480000.00"],
            "description": "Decimal amount serialised as a string to preserve precision.",
        }
    ),
]
MoneyStr = Money


def _is_money_annotation(annotation: Any) -> bool:
    origin = typing.get_origin(annotation)
    if origin is Annotated:
        args = typing.get_args(annotation)
        if any(isinstance(meta, _MoneyMarker) for meta in args[1:]):
            return True
        return _is_money_annotation(args[0])
    if origin is typing.Union or origin is types.UnionType:
        return any(_is_money_annotation(arg) for arg in typing.get_args(annotation))
    return False


def _currency_source(model: type[BaseModel], field_name: str) -> str | None:
    tokens = field_name.split("_")
    if "usd" in tokens:
        return USD_CURRENCY_SOURCE
    if field_name.startswith("fee_") and "fee_currency" in model.model_fields:
        return "fee_currency"
    if "currency" in model.model_fields:
        return "currency"
    return None


def _discover_money_fields(model: type[BaseModel]) -> dict[str, tuple[str, str | None]]:
    discovered: dict[str, tuple[str, str | None]] = {}
    for name, field in model.model_fields.items():
        marked = any(isinstance(meta, _MoneyMarker) for meta in field.metadata)
        if not marked and not _is_money_annotation(field.annotation):
            continue
        alias = field.serialization_alias or field.alias or name
        discovered[name] = (alias, _currency_source(model, name))
    return discovered


class ApiModel(BaseModel):
    """Base model for the API contract (ORM-friendly, currency-aware money output)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="ignore")

    __money_fields__: ClassVar[dict[str, tuple[str, str | None]]] = {}

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        cls.__money_fields__ = _discover_money_fields(cls)

    def _minor_units_for(self, source: str | None) -> int | None:
        if source is None:
            return None
        if source == USD_CURRENCY_SOURCE:
            return 2
        return minor_units_or_none(getattr(self, source, None))

    @model_serializer(mode="wrap")
    def _serialize_with_money(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Any:
        data = handler(self)
        if info.mode != "json" or not self.__money_fields__ or not isinstance(data, dict):
            return data
        for name, (alias, source) in self.__money_fields__.items():
            key = alias if info.by_alias else name
            if key not in data:
                continue
            raw = getattr(self, name, None)
            if isinstance(raw, Decimal):
                data[key] = format_money(raw, self._minor_units_for(source))
        return data


class RequestModel(ApiModel):
    """Base for request bodies: unknown fields are rejected, strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Page[T](ApiModel):
    """List envelope used by every collection endpoint."""

    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)

    @classmethod
    def build(cls, items: Sequence[T], *, page: int, page_size: int, total: int) -> Page[T]:
        return cls(items=list(items), page=page, page_size=page_size, total=total)


class PageQuery(BaseModel):
    """Pagination query parameters (``?page=1&page_size=25``)."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class UserRef(ApiModel):
    username: str
    display_name: str


class ProblemError(ApiModel):
    loc: list[str | int] = Field(default_factory=list)
    msg: str
    type: str


class ProblemDetails(ApiModel):
    """``application/problem+json`` body (RFC 9457) with the request correlation id."""

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    correlation_id: str | None = None
    errors: list[ProblemError] | None = None


PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "description": "Unknown demo identity"},
    403: {"model": ProblemDetails, "description": "Role not permitted"},
    404: {"model": ProblemDetails, "description": "Not found"},
    409: {"model": ProblemDetails, "description": "Invalid state transition or conflict"},
    422: {"model": ProblemDetails, "description": "Validation failed"},
}
