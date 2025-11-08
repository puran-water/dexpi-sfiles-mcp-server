"""Tests for DEXPI enumeration imports.

These tests verify that ALL DEXPI enumerations are correctly imported from
pyDEXPI and that fallbacks match the upstream values.
"""

import pytest
from src.models.dexpi_enums import DEXPI_AVAILABLE


class TestDEXPIEnumAvailability:
    """Test that DEXPI enums are available."""

    def test_dexpi_available_flag(self):
        """Test DEXPI_AVAILABLE flag is set correctly."""
        # Should be True if pyDEXPI installed, False otherwise
        assert isinstance(DEXPI_AVAILABLE, bool)

    def test_import_all_enums(self):
        """Test that all expected enums can be imported."""
        # This test documents all enums we expect to have
        from src.models.dexpi_enums import (
            # Port/Valve
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
            # Safety
            DetonationProofArtefactClassification,
            ExplosionProofArtefactClassification,
            FireResistantArtefactClassification,
            # Quality
            GmpRelevanceClassification,
            QualityRelevanceClassification,
            ConfidentialityClassification,
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
            # Drawing
            DashStyle,
            FillStyle,
            TextAlignment,
        )

        # All imports should succeed
        assert NumberOfPortsClassification is not None
        assert OperationClassification is not None


class TestPortValveEnums:
    """Test port and valve classification enums."""

    def test_number_of_ports_classification(self):
        """Test NumberOfPortsClassification has expected values."""
        from src.models.dexpi_enums import NumberOfPortsClassification

        assert hasattr(NumberOfPortsClassification, "TwoPortValve")
        assert hasattr(NumberOfPortsClassification, "ThreePortValve")
        assert hasattr(NumberOfPortsClassification, "FourPortValve")
        assert hasattr(NumberOfPortsClassification, "NULL")

        # Values should match DEXPI spec
        assert NumberOfPortsClassification.TwoPortValve.value == "2 port valve"
        assert NumberOfPortsClassification.ThreePortValve.value == "3 port valve"
        assert NumberOfPortsClassification.FourPortValve.value == "4 port valve"

    def test_port_status_classification(self):
        """Test PortStatusClassification has expected values."""
        from src.models.dexpi_enums import PortStatusClassification

        assert hasattr(PortStatusClassification, "StatusHighPort")
        assert hasattr(PortStatusClassification, "StatusLowPort")
        assert hasattr(PortStatusClassification, "NULL")

        # Values should match DEXPI spec
        assert PortStatusClassification.StatusHighPort.value == "H"
        assert PortStatusClassification.StatusLowPort.value == "L"


class TestEquipmentOperationEnums:
    """Test equipment operation classification enums."""

    def test_operation_classification(self):
        """Test OperationClassification has expected values."""
        from src.models.dexpi_enums import OperationClassification

        assert hasattr(OperationClassification, "ContinuousOperation")
        assert hasattr(OperationClassification, "IntermittentOperation")
        assert hasattr(OperationClassification, "NULL")

        # Values should match DEXPI spec
        assert OperationClassification.ContinuousOperation.value == "continuous operation"
        assert OperationClassification.IntermittentOperation.value == "intermittent operation"

    def test_location_classification(self):
        """Test LocationClassification has expected values."""
        from src.models.dexpi_enums import LocationClassification

        assert hasattr(LocationClassification, "CentralLocation")
        assert hasattr(LocationClassification, "ControlPanel")
        assert hasattr(LocationClassification, "Field")
        assert hasattr(LocationClassification, "NULL")

        # Values should match DEXPI spec
        assert LocationClassification.CentralLocation.value == "central"
        assert LocationClassification.ControlPanel.value == "panel"
        assert LocationClassification.Field.value == "field"


class TestControlInstrumentationEnums:
    """Test control and instrumentation classification enums."""

    def test_fail_action_classification(self):
        """Test FailActionClassification has expected values."""
        from src.models.dexpi_enums import FailActionClassification

        assert hasattr(FailActionClassification, "FailClose")
        assert hasattr(FailActionClassification, "FailOpen")
        assert hasattr(FailActionClassification, "FailRetainPosition")
        assert hasattr(FailActionClassification, "NULL")

        # Values should match DEXPI spec
        assert FailActionClassification.FailClose.value == "fail close"
        assert FailActionClassification.FailOpen.value == "fail open"
        assert FailActionClassification.FailRetainPosition.value == "fail retain position"

    def test_signal_conveying_type_classification(self):
        """Test SignalConveyingTypeClassification has expected values."""
        from src.models.dexpi_enums import SignalConveyingTypeClassification

        assert hasattr(SignalConveyingTypeClassification, "ElectricalSignalConveying")
        assert hasattr(SignalConveyingTypeClassification, "PneumaticSignalConveying")
        assert hasattr(SignalConveyingTypeClassification, "HydraulicSignalConveying")
        assert hasattr(SignalConveyingTypeClassification, "NULL")

        # Values should match DEXPI spec
        assert SignalConveyingTypeClassification.ElectricalSignalConveying.value == "electrical"
        assert SignalConveyingTypeClassification.PneumaticSignalConveying.value == "pneumatic"
        assert SignalConveyingTypeClassification.HydraulicSignalConveying.value == "hydraulic"


class TestPipingEnums:
    """Test piping classification enums."""

    def test_piping_network_segment_flow_classification(self):
        """Test PipingNetworkSegmentFlowClassification has expected values."""
        from src.models.dexpi_enums import PipingNetworkSegmentFlowClassification

        assert hasattr(PipingNetworkSegmentFlowClassification, "SingleFlowPipingNetworkSegment")
        assert hasattr(PipingNetworkSegmentFlowClassification, "DualFlowPipingNetworkSegment")
        assert hasattr(PipingNetworkSegmentFlowClassification, "NULL")

        # Values should match DEXPI spec
        assert PipingNetworkSegmentFlowClassification.SingleFlowPipingNetworkSegment.value == "single flow"
        assert PipingNetworkSegmentFlowClassification.DualFlowPipingNetworkSegment.value == "dual flow"


class TestEngineeringUnitEnums:
    """Test engineering unit enums."""

    def test_unit_enums_exist(self):
        """Test that all unit enums can be imported."""
        from src.models.dexpi_enums import (
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
        )

        # All should be importable
        assert AreaUnit is not None
        assert TemperatureUnit is not None
        assert PressureAbsoluteUnit is not None


class TestModuleIntegration:
    """Test integration with port_spec and other modules."""

    def test_port_spec_uses_dexpi_enums(self):
        """Test that port_spec imports from dexpi_enums module."""
        from src.models.port_spec import NumberOfPortsClassification, PortStatusClassification
        from src.models.dexpi_enums import (
            NumberOfPortsClassification as EnumNumberOfPorts,
            PortStatusClassification as EnumPortStatus,
        )

        # Should be the same class (not a copy)
        assert NumberOfPortsClassification is EnumNumberOfPorts
        assert PortStatusClassification is EnumPortStatus

    def test_dexpi_enums_exported_from_models(self):
        """Test that dexpi_enums module is exported from src.models."""
        from src.models import dexpi_enums

        assert dexpi_enums.DEXPI_AVAILABLE is not None
        assert hasattr(dexpi_enums, "NumberOfPortsClassification")
        assert hasattr(dexpi_enums, "OperationClassification")
        assert hasattr(dexpi_enums, "FailActionClassification")


@pytest.mark.skipif(not DEXPI_AVAILABLE, reason="pyDEXPI not installed")
class TestDEXPIUpstreamCompatibility:
    """Test compatibility with actual pyDEXPI enumerations (only if installed)."""

    def test_enums_are_from_pydexpi(self):
        """Test that we're using actual pyDEXPI enums, not fallbacks."""
        import pydexpi.dexpi_classes.pydantic_classes as pydexpi_classes
        from src.models.dexpi_enums import (
            NumberOfPortsClassification,
            OperationClassification,
            FailActionClassification,
        )

        # Should be the SAME class (identity check)
        assert NumberOfPortsClassification is pydexpi_classes.NumberOfPortsClassification
        assert OperationClassification is pydexpi_classes.OperationClassification
        assert FailActionClassification is pydexpi_classes.FailActionClassification

    def test_all_pydexpi_enums_imported(self):
        """Test that we import all enums from pyDEXPI."""
        import inspect
        import pydexpi.dexpi_classes.pydantic_classes as pydexpi_classes
        from src.models import dexpi_enums

        # Get all enum classes from pyDEXPI
        pydexpi_enum_names = {
            name
            for name, obj in inspect.getmembers(pydexpi_classes)
            if inspect.isclass(obj)
            and hasattr(obj, "__bases__")
            and any("Enum" in str(base) for base in obj.__bases__)
        }

        # Get all enum classes from our module
        our_enum_names = {
            name
            for name in dexpi_enums.__all__
            if name != "DEXPI_AVAILABLE"
        }

        # We should have imported all of them
        missing_enums = pydexpi_enum_names - our_enum_names
        assert len(missing_enums) == 0, f"Missing enums: {missing_enums}"
