"""DEXPI enumeration re-exports from pyDEXPI.

This module imports and re-exports ALL DEXPI enumerations from pyDEXPI's
pydantic_classes module. This ensures we leverage upstream definitions
without reinventing them.

Architecture Decision (Codex Review #3):
    "Import enumerations from pyDEXPI. Don't create separate enums that might
    conflict with DEXPI's official enumerations. Prefer exposing existing enums."

Categories:
    - Port/Valve: NumberOfPortsClassification, PortStatusClassification
    - Equipment Operation: OperationClassification, LocationClassification
    - Control/Instrumentation: FailActionClassification, SignalConveyingTypeClassification
    - Piping: PipingNetworkSegmentFlowClassification, NominalDiameterStandardClassification
    - Units: All engineering unit enumerations
    - Classification: GmpRelevanceClassification, ConfidentialityClassification, etc.

Requirements:
    pyDEXPI must be installed. This module will raise ImportError if not available.
"""

import logging

logger = logging.getLogger(__name__)

# Import ALL DEXPI enumerations from pyDEXPI (fail loudly if not installed)
try:
    from pydexpi.dexpi_classes.pydantic_classes import (
        # Port/Valve Classifications
        NumberOfPortsClassification,
        PortStatusClassification,

        # Equipment Operation
        OperationClassification,
        LocationClassification,

        # Control/Instrumentation
        FailActionClassification,
        SignalConveyingTypeClassification,

        # Piping
        PipingNetworkSegmentFlowClassification,
        PipingNetworkSegmentSlopeClassification,
        PrimarySecondaryPipingNetworkSegmentClassification,
        NominalDiameterStandardClassification,
        NominalPressureStandardClassification,
        NominalDiameterBreakClassification,
        PipingClassBreakClassification,
        PipingClassArtefactClassification,
        JacketedPipeClassification,
        SiphonClassification,

        # Chamber/Vessel
        ChamberFunctionClassification,
        CompositionBreakClassification,
        InsulationBreakClassification,

        # Safety/Protection
        DetonationProofArtefactClassification,
        ExplosionProofArtefactClassification,
        FireResistantArtefactClassification,

        # Quality/Compliance
        GmpRelevanceClassification,
        QualityRelevanceClassification,
        ConfidentialityClassification,
        OnHoldClassification,

        # System Classifications
        GuaranteedSupplyFunctionClassification,
        HeatTracingTypeClassification,

        # Engineering Units
        AreaUnit,
        ForceUnit,
        LengthUnit,
        MassUnit,
        MassFlowRateUnit,
        PowerUnit,
        PressureAbsoluteUnit,
        PressureGaugeUnit,
        TemperatureUnit,
        VolumeUnit,
        VolumeFlowRateUnit,
        ElectricalFrequencyUnit,
        RotationalFrequencyUnit,
        HeatTransferCoefficientUnit,
        NumberPerTimeIntervalUnit,
        PercentageUnit,
        VoltageUnit,

        # Drawing/Rendering
        AttributeRepresentationType,
        DashStyle,
        FillStyle,
        TextAlignment,
    )
    DEXPI_AVAILABLE = True
    logger.info("Successfully imported all DEXPI enumerations from pyDEXPI")

except ImportError as e:
    logger.error(
        f"CRITICAL: pyDEXPI not installed or import failed: {e}\n"
        "pyDEXPI is a REQUIRED dependency for engineering-mcp-server.\n"
        "Install with: pip install pydexpi\n"
        "See: https://github.com/process-intelligence-research/pyDEXPI"
    )
    raise ImportError(
        "pyDEXPI is required but not installed. "
        "Install with: pip install pydexpi"
    ) from e


# Re-export all enums for convenience
__all__ = [
    # Availability flag
    "DEXPI_AVAILABLE",

    # Port/Valve
    "NumberOfPortsClassification",
    "PortStatusClassification",

    # Equipment Operation
    "OperationClassification",
    "LocationClassification",

    # Control/Instrumentation
    "FailActionClassification",
    "SignalConveyingTypeClassification",

    # Piping
    "PipingNetworkSegmentFlowClassification",
    "PipingNetworkSegmentSlopeClassification",
    "PrimarySecondaryPipingNetworkSegmentClassification",
    "NominalDiameterStandardClassification",
    "NominalPressureStandardClassification",
    "NominalDiameterBreakClassification",
    "PipingClassBreakClassification",
    "PipingClassArtefactClassification",
    "JacketedPipeClassification",
    "SiphonClassification",

    # Chamber/Vessel
    "ChamberFunctionClassification",
    "CompositionBreakClassification",
    "InsulationBreakClassification",

    # Safety/Protection
    "DetonationProofArtefactClassification",
    "ExplosionProofArtefactClassification",
    "FireResistantArtefactClassification",

    # Quality/Compliance
    "GmpRelevanceClassification",
    "QualityRelevanceClassification",
    "ConfidentialityClassification",
    "OnHoldClassification",

    # System Classifications
    "GuaranteedSupplyFunctionClassification",
    "HeatTracingTypeClassification",

    # Engineering Units
    "AreaUnit",
    "ForceUnit",
    "LengthUnit",
    "MassUnit",
    "MassFlowRateUnit",
    "PowerUnit",
    "PressureAbsoluteUnit",
    "PressureGaugeUnit",
    "TemperatureUnit",
    "VolumeUnit",
    "VolumeFlowRateUnit",
    "ElectricalFrequencyUnit",
    "RotationalFrequencyUnit",
    "HeatTransferCoefficientUnit",
    "NumberPerTimeIntervalUnit",
    "PercentageUnit",
    "VoltageUnit",

    # Drawing/Rendering
    "AttributeRepresentationType",
    "DashStyle",
    "FillStyle",
    "TextAlignment",
]
