"""Utilities for coercing Graph Modify payloads into valid pyDEXPI objects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from numbers import Number
import types
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type, Union, get_args, get_origin

from pydantic import TypeAdapter, ValidationError
from pydexpi.dexpi_classes.pydantic_classes import (
    Area,
    AreaUnit,
    ElectricalFrequency,
    ElectricalFrequencyUnit,
    Force,
    ForceUnit,
    HeatTransferCoefficient,
    HeatTransferCoefficientUnit,
    Length,
    LengthUnit,
    Mass,
    MassUnit,
    MassFlowRate,
    MassFlowRateUnit,
    MultiLanguageString,
    NullableArea,
    NullableElectricalFrequency,
    NullableForce,
    NullableHeatTransferCoefficient,
    NullableLength,
    NullableMass,
    NullableMassFlowRate,
    NullableNumberPerTimeInterval,
    NullablePercentage,
    NullablePower,
    NullablePressureAbsolute,
    NullablePressureGauge,
    NullableRotationalFrequency,
    NullableTemperature,
    NullableVoltage,
    NullableVolume,
    NullableVolumeFlowRate,
    NumberPerTimeInterval,
    NumberPerTimeIntervalUnit,
    Percentage,
    PercentageUnit,
    Power,
    PowerUnit,
    PressureAbsolute,
    PressureAbsoluteUnit,
    PressureGauge,
    PressureGaugeUnit,
    RotationalFrequency,
    RotationalFrequencyUnit,
    SingleLanguageString,
    Temperature,
    TemperatureUnit,
    Voltage,
    VoltageUnit,
    Volume,
    VolumeFlowRate,
    VolumeFlowRateUnit,
    VolumeUnit,
)

DEFAULT_LANGUAGE = "en"
_VALUE_UNIT_PATTERN = re.compile(
    r"^\s*(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(?P<unit>.*)$"
)


class DexpiAttributeConversionError(Exception):
    """Raised when an attribute payload cannot be coerced into a valid value."""

    def __init__(self, attribute: str, message: str, code: str = "INVALID_VALUE"):
        super().__init__(message)
        self.attribute = attribute
        self.code = code
        self.message = message

    def to_issue(self) -> Dict[str, Any]:
        return {"attribute": self.attribute, "code": self.code, "message": self.message}


@dataclass(frozen=True)
class QuantitySpec:
    """Specification for a physical quantity that carries a unit."""

    value_type: Type
    unit_enum: Type
    default_unit: Any


def _register_quantity(
    registry: Dict[Type, QuantitySpec],
    spec: QuantitySpec,
    *aliases: Type,
) -> None:
    """Register the spec for its primary type and nullable aliases."""
    for type_alias in (spec.value_type, *aliases):
        registry[type_alias] = spec


class DexpiAttributeSanitizer:
    """Sanitize user-provided attribute dictionaries for pyDEXPI models."""

    def __init__(self, default_language: str = DEFAULT_LANGUAGE):
        self._type_adapter_cache: Dict[Any, TypeAdapter[Any]] = {}
        self._default_language = default_language
        self._quantity_specs = self._build_quantity_specs()

    def sanitize(
        self,
        component: Any,
        attributes: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Return sanitized attributes and an error list (if any)."""
        sanitized: Dict[str, Any] = {}
        issues: List[Dict[str, Any]] = []
        model_fields = getattr(type(component), "model_fields", {})

        for attr_name, raw_value in attributes.items():
            if attr_name not in model_fields:
                issues.append(
                    {
                        "attribute": attr_name,
                        "code": "UNKNOWN_ATTRIBUTE",
                        "message": f"{type(component).__name__} has no attribute '{attr_name}'",
                    }
                )
                continue

            field_info = model_fields[attr_name]
            try:
                sanitized[attr_name] = self._convert_value(
                    attr_name,
                    field_info.annotation,
                    raw_value,
                )
            except DexpiAttributeConversionError as exc:
                issues.append(exc.to_issue())

        return sanitized, issues

    def _convert_value(
        self,
        attribute: str,
        annotation: Any,
        raw_value: Any,
    ) -> Any:
        if raw_value is None:
            return None

        if self._is_multilanguage(annotation):
            return self._coerce_multilanguage(attribute, raw_value)

        quantity_spec = self._resolve_quantity_spec(annotation)
        if quantity_spec:
            return self._coerce_quantity(attribute, quantity_spec, raw_value)

        adapter = self._get_type_adapter(annotation)
        try:
            return adapter.validate_python(raw_value)
        except ValidationError as exc:
            raise DexpiAttributeConversionError(
                attribute,
                f"Value '{raw_value}' is not valid for {annotation!r}: {exc.errors()}",
            ) from exc

    def _coerce_multilanguage(
        self,
        attribute: str,
        raw_value: Any,
    ) -> MultiLanguageString | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, MultiLanguageString):
            return raw_value
        if isinstance(raw_value, SingleLanguageString):
            return MultiLanguageString(singleLanguageStrings=[raw_value])

        entries: List[SingleLanguageString] = []
        if isinstance(raw_value, dict):
            if "singleLanguageStrings" in raw_value:
                entries.extend(
                    self._coerce_single_language_sequence(
                        attribute,
                        raw_value["singleLanguageStrings"],
                    )
                )
            elif "language" in raw_value or "value" in raw_value or "text" in raw_value:
                entries.append(self._build_single_language(attribute, raw_value))
            else:
                for lang, text in raw_value.items():
                    entries.append(
                        SingleLanguageString(
                            language=lang or self._default_language,
                            value=None if text is None else str(text),
                        )
                    )
        elif isinstance(raw_value, (list, tuple)):
            entries.extend(
                self._coerce_single_language_sequence(attribute, raw_value)
            )
        elif isinstance(raw_value, (str, Number)):
            entries.append(
                SingleLanguageString(
                    language=self._default_language,
                    value=str(raw_value),
                )
            )
        else:
            raise DexpiAttributeConversionError(
                attribute,
                f"Cannot coerce value of type {type(raw_value).__name__} into MultiLanguageString",
            )

        if not entries:
            raise DexpiAttributeConversionError(
                attribute,
                "MultiLanguageString requires at least one entry",
            )

        return MultiLanguageString(singleLanguageStrings=entries)

    def _coerce_single_language_sequence(
        self,
        attribute: str,
        items: Any,
    ) -> List[SingleLanguageString]:
        if not isinstance(items, (list, tuple)):
            items = [items]
        result: List[SingleLanguageString] = []
        for item in items:
            if isinstance(item, SingleLanguageString):
                result.append(item)
            elif isinstance(item, dict):
                result.append(self._build_single_language(attribute, item))
            elif isinstance(item, (str, Number)):
                result.append(
                    SingleLanguageString(
                        language=self._default_language,
                        value=str(item),
                    )
                )
            else:
                raise DexpiAttributeConversionError(
                    attribute,
                    f"Unsupported entry type {type(item).__name__} for MultiLanguageString",
                )
        return result

    def _build_single_language(
        self,
        attribute: str,
        payload: Dict[str, Any],
    ) -> SingleLanguageString:
        language = payload.get("language") or payload.get("lang") or self._default_language
        value = payload.get("value", payload.get("text"))
        if value is not None:
            value = str(value)
        return SingleLanguageString(language=language, value=value)

    def _coerce_quantity(
        self,
        attribute: str,
        spec: QuantitySpec,
        raw_value: Any,
    ) -> Any:
        if isinstance(raw_value, spec.value_type):
            return raw_value

        value: Optional[float] = None
        unit_input: Any = None

        if isinstance(raw_value, dict):
            value = self._to_float(
                raw_value.get("value")
                or raw_value.get("numericalValue")
                or raw_value.get("amount")
            )
            unit_input = (
                raw_value.get("unit")
                or raw_value.get("units")
                or raw_value.get("unitName")
            )
        elif isinstance(raw_value, Number):
            value = float(raw_value)
        elif isinstance(raw_value, str):
            match = _VALUE_UNIT_PATTERN.match(raw_value)
            if not match:
                raise DexpiAttributeConversionError(
                    attribute,
                    f"Unable to parse numeric value from '{raw_value}'",
                )
            value = float(match.group("value"))
            unit_input = match.group("unit").strip() or None
        else:
            raise DexpiAttributeConversionError(
                attribute,
                f"Cannot coerce value of type {type(raw_value).__name__} into {spec.value_type.__name__}",
            )

        if value is None:
            raise DexpiAttributeConversionError(
                attribute,
                "Missing numerical value for quantity",
            )

        unit = self._normalize_unit(attribute, spec, unit_input)
        return spec.value_type(unit=unit, value=float(value))

    def _normalize_unit(
        self,
        attribute: str,
        spec: QuantitySpec,
        unit_input: Any,
    ) -> Any:
        if unit_input is None:
            return spec.default_unit
        if isinstance(unit_input, spec.unit_enum):
            return unit_input
        if isinstance(unit_input, str):
            normalized = unit_input.strip()
            if not normalized:
                return spec.default_unit
            try:
                return spec.unit_enum[normalized]
            except KeyError:
                pass
            normalized_lower = normalized.lower()
            for member in spec.unit_enum:
                if member.value.lower() == normalized_lower or member.name.lower() == normalized_lower.replace(" ", "_"):
                    return member
        raise DexpiAttributeConversionError(
            attribute,
            f"Unknown unit '{unit_input}' for {spec.unit_enum.__name__}",
        )

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, Number):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            return float(stripped)
        return None

    def _is_multilanguage(self, annotation: Any) -> bool:
        return any(self._is_type(candidate, MultiLanguageString) for candidate in self._flatten_types(annotation))

    def _resolve_quantity_spec(self, annotation: Any) -> Optional[QuantitySpec]:
        for candidate in self._flatten_types(annotation):
            spec = self._quantity_specs.get(candidate)
            if spec:
                return spec
        return None

    def _flatten_types(self, annotation: Any) -> Iterable[Type]:
        if isinstance(annotation, types.UnionType):
            for arg in annotation.__args__:
                yield from self._flatten_types(arg)
            return

        origin = get_origin(annotation)
        if origin is None:
            yield annotation
            return
        if origin is Union:
            for arg in get_args(annotation):
                yield from self._flatten_types(arg)
            return
        if origin in (list, tuple, List, Tuple):
            for arg in get_args(annotation):
                yield from self._flatten_types(arg)
            return
        yield annotation

    def _is_type(self, candidate: Any, target: Type) -> bool:
        try:
            return candidate is target or issubclass(candidate, target)
        except TypeError:
            return False

    def _get_type_adapter(self, annotation: Any) -> TypeAdapter[Any]:
        cache_key = id(annotation)
        adapter = self._type_adapter_cache.get(cache_key)
        if adapter is None:
            adapter = TypeAdapter(annotation)
            self._type_adapter_cache[cache_key] = adapter
        return adapter

    def _build_quantity_specs(self) -> Dict[Type, QuantitySpec]:
        specs: Dict[Type, QuantitySpec] = {}

        _register_quantity(
            specs,
            QuantitySpec(Area, AreaUnit, AreaUnit.MetreSquared),
            NullableArea,
        )
        _register_quantity(
            specs,
            QuantitySpec(ElectricalFrequency, ElectricalFrequencyUnit, ElectricalFrequencyUnit.Hertz),
            NullableElectricalFrequency,
        )
        _register_quantity(
            specs,
            QuantitySpec(Force, ForceUnit, ForceUnit.Newton),
            NullableForce,
        )
        _register_quantity(
            specs,
            QuantitySpec(
                HeatTransferCoefficient,
                HeatTransferCoefficientUnit,
                HeatTransferCoefficientUnit.WattPerMetreSquaredKelvin,
            ),
            NullableHeatTransferCoefficient,
        )
        _register_quantity(
            specs,
            QuantitySpec(Length, LengthUnit, LengthUnit.Metre),
            NullableLength,
        )
        _register_quantity(
            specs,
            QuantitySpec(Mass, MassUnit, MassUnit.Kilogram),
            NullableMass,
        )
        _register_quantity(
            specs,
            QuantitySpec(MassFlowRate, MassFlowRateUnit, MassFlowRateUnit.KilogramPerSecond),
            NullableMassFlowRate,
        )
        _register_quantity(
            specs,
            QuantitySpec(
                NumberPerTimeInterval,
                NumberPerTimeIntervalUnit,
                NumberPerTimeIntervalUnit.ReciprocalSecond,
            ),
            NullableNumberPerTimeInterval,
        )
        _register_quantity(
            specs,
            QuantitySpec(Percentage, PercentageUnit, PercentageUnit.Percent),
            NullablePercentage,
        )
        _register_quantity(
            specs,
            QuantitySpec(Power, PowerUnit, PowerUnit.Watt),
            NullablePower,
        )
        _register_quantity(
            specs,
            QuantitySpec(PressureAbsolute, PressureAbsoluteUnit, PressureAbsoluteUnit.Pascal),
            NullablePressureAbsolute,
        )
        _register_quantity(
            specs,
            QuantitySpec(PressureGauge, PressureGaugeUnit, PressureGaugeUnit.Bar),
            NullablePressureGauge,
        )
        _register_quantity(
            specs,
            QuantitySpec(RotationalFrequency, RotationalFrequencyUnit, RotationalFrequencyUnit.ReciprocalMinute),
            NullableRotationalFrequency,
        )
        _register_quantity(
            specs,
            QuantitySpec(Temperature, TemperatureUnit, TemperatureUnit.DegreeCelsius),
            NullableTemperature,
        )
        _register_quantity(
            specs,
            QuantitySpec(Voltage, VoltageUnit, VoltageUnit.Volt),
            NullableVoltage,
        )
        _register_quantity(
            specs,
            QuantitySpec(Volume, VolumeUnit, VolumeUnit.MetreCubed),
            NullableVolume,
        )
        _register_quantity(
            specs,
            QuantitySpec(VolumeFlowRate, VolumeFlowRateUnit, VolumeFlowRateUnit.MetreCubedPerHour),
            NullableVolumeFlowRate,
        )

        return specs
