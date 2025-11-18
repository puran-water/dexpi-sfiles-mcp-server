"""Baseline fidelity measurement tests.

These tests measure current export fidelity WITHOUT assertions to establish
realistic threshold values for Task 5.
"""

import pytest
from lxml import etree

from src.exporters.proteus_xml_exporter import ProteusXMLExporter
from src.core.analytics.model_metrics import calculate_export_fidelity

# Import fixtures from the main test file
pytest_plugins = ["tests.exporters.test_proteus_xml_exporter"]


class TestBaselineFidelity:
    """Measure baseline export fidelity for existing fixtures.

    These tests verify that export fidelity meets the 80% threshold
    and that no data attributes are missing from exports.
    """

    def test_baseline_tank_fidelity(self, empty_model, tank_with_nozzles, tmp_path, capsys):
        """Test Tank fixture meets fidelity threshold with no missing attributes."""
        # Add tank to model and export
        empty_model.conceptualModel.taggedPlantItems = [tank_with_nozzles]
        output_file = tmp_path / "tank_baseline.xml"

        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Parse exported XML and find the Equipment element
        tree = etree.parse(str(output_file))
        root = tree.getroot()
        xml_elem = root.find(".//Equipment[@ID='TANK-001']")

        assert xml_elem is not None, "Tank element not found in export"

        # Calculate fidelity with strict validation
        result = calculate_export_fidelity(
            component=tank_with_nozzles,
            exported_element=xml_elem,
            threshold=0.80,
            fail_below_threshold=True  # Fail loudly on low fidelity
        )

        # Print results for visibility
        print(f"\n[Tank] Fidelity: {result['fidelity_percent']:.2f}% ({result['exported_count']}/{result['source_count']})")

        # Assert no missing attributes (critical for data quality)
        assert result['missing_attributes'] == [], \
            f"Tank has missing attributes: {result['missing_attributes']}"

        # Assert status is PASS
        assert result['status'] == "PASS", \
            f"Tank fidelity {result['fidelity_percent']}% below 80% threshold"

    def test_baseline_pump_fidelity(self, empty_model, pump, tmp_path, capsys):
        """Test CentrifugalPump fixture meets fidelity threshold with no missing attributes."""
        # Add pump to model and export
        empty_model.conceptualModel.taggedPlantItems = [pump]
        output_file = tmp_path / "pump_baseline.xml"

        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Parse exported XML and find the Equipment element
        tree = etree.parse(str(output_file))
        root = tree.getroot()
        xml_elem = root.find(".//Equipment[@ID='PMP-001']")

        assert xml_elem is not None, "Pump element not found in export"

        # Calculate fidelity with strict validation
        result = calculate_export_fidelity(
            component=pump,
            exported_element=xml_elem,
            threshold=0.80,
            fail_below_threshold=True
        )

        print(f"\n[Pump] Fidelity: {result['fidelity_percent']:.2f}% ({result['exported_count']}/{result['source_count']})")

        assert result['missing_attributes'] == [], \
            f"Pump has missing attributes: {result['missing_attributes']}"
        assert result['status'] == "PASS", \
            f"Pump fidelity {result['fidelity_percent']}% below 80% threshold"

    def test_baseline_heat_exchanger_fidelity(self, empty_model, heat_exchanger, tmp_path, capsys):
        """Test PlateHeatExchanger fixture meets fidelity threshold with no missing attributes."""
        # Add heat exchanger to model and export
        empty_model.conceptualModel.taggedPlantItems = [heat_exchanger]
        output_file = tmp_path / "hx_baseline.xml"

        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Parse exported XML and find the Equipment element
        tree = etree.parse(str(output_file))
        root = tree.getroot()
        xml_elem = root.find(".//Equipment[@ID='HEX-001']")

        assert xml_elem is not None, "HeatExchanger element not found in export"

        # Calculate fidelity with strict validation
        result = calculate_export_fidelity(
            component=heat_exchanger,
            exported_element=xml_elem,
            threshold=0.80,
            fail_below_threshold=True
        )

        print(f"\n[HX] Fidelity: {result['fidelity_percent']:.2f}% ({result['exported_count']}/{result['source_count']})")

        assert result['missing_attributes'] == [], \
            f"HeatExchanger has missing attributes: {result['missing_attributes']}"
        assert result['status'] == "PASS", \
            f"HeatExchanger fidelity {result['fidelity_percent']}% below 80% threshold"

    def test_baseline_piping_fidelity(self, empty_model, simple_piping_segment, tmp_path, capsys):
        """Test PipingNetworkSegment fixture meets fidelity threshold with no missing attributes."""
        # Add piping to model and export
        from pydexpi.dexpi_classes import piping as piping_module

        piping_system = piping_module.PipingNetworkSystem()
        piping_system.id = "PS-001"
        piping_system.segments = [simple_piping_segment]

        empty_model.conceptualModel.pipingNetworkSystems = [piping_system]
        output_file = tmp_path / "piping_baseline.xml"

        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Parse exported XML and find the PipingNetworkSegment element
        tree = etree.parse(str(output_file))
        root = tree.getroot()
        xml_elem = root.find(".//PipingNetworkSegment[@ID='SEG-001']")

        assert xml_elem is not None, "PipingNetworkSegment element not found in export"

        # Calculate fidelity with strict validation
        result = calculate_export_fidelity(
            component=simple_piping_segment,
            exported_element=xml_elem,
            threshold=0.80,
            fail_below_threshold=True
        )

        print(f"\n[Piping] Fidelity: {result['fidelity_percent']:.2f}% ({result['exported_count']}/{result['source_count']})")

        assert result['missing_attributes'] == [], \
            f"Piping has missing attributes: {result['missing_attributes']}"
        assert result['status'] == "PASS", \
            f"Piping fidelity {result['fidelity_percent']}% below 80% threshold"

    def test_baseline_instrumentation_fidelity(self, empty_model, instrumentation_function_with_sensor, tmp_path, capsys):
        """Test ProcessInstrumentationFunction fixture meets fidelity threshold with no missing attributes."""
        # Add instrumentation to model and export
        empty_model.conceptualModel.processInstrumentationFunctions = [instrumentation_function_with_sensor]
        output_file = tmp_path / "instrumentation_baseline.xml"

        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Parse exported XML and find the ProcessInstrumentationFunction element
        tree = etree.parse(str(output_file))
        root = tree.getroot()
        xml_elem = root.find(".//ProcessInstrumentationFunction[@ID='INS-001']")

        assert xml_elem is not None, "ProcessInstrumentationFunction element not found in export"

        # Calculate fidelity with strict validation
        result = calculate_export_fidelity(
            component=instrumentation_function_with_sensor,
            exported_element=xml_elem,
            threshold=0.80,
            fail_below_threshold=True
        )

        print(f"\n[Instrumentation] Fidelity: {result['fidelity_percent']:.2f}% ({result['exported_count']}/{result['source_count']})")

        assert result['missing_attributes'] == [], \
            f"Instrumentation has missing attributes: {result['missing_attributes']}"
        assert result['status'] == "PASS", \
            f"Instrumentation fidelity {result['fidelity_percent']}% below 80% threshold"

    def test_baseline_instrumentation_loop_fidelity(self, empty_model, tmp_path, capsys):
        """Test InstrumentationLoopFunction fixture meets fidelity threshold with no missing attributes."""
        from pydexpi.dexpi_classes import instrumentation as inst_module

        # Create InstrumentationLoopFunction with loop number
        loop_func = inst_module.InstrumentationLoopFunction()
        loop_func.id = "LOOP-FIDELITY-001"
        loop_func.instrumentationLoopFunctionNumber = "FIC-101"

        # Add to model and export
        empty_model.conceptualModel.instrumentationLoopFunctions = [loop_func]
        output_file = tmp_path / "loop_baseline.xml"

        exporter = ProteusXMLExporter()
        exporter.export(empty_model, output_file, validate=False)

        # Parse exported XML and find the InstrumentationLoopFunction element
        tree = etree.parse(str(output_file))
        root = tree.getroot()
        xml_elem = root.find(".//InstrumentationLoopFunction[@ID='LOOP-FIDELITY-001']")

        assert xml_elem is not None, "InstrumentationLoopFunction element not found in export"

        # Calculate fidelity with strict validation
        result = calculate_export_fidelity(
            component=loop_func,
            exported_element=xml_elem,
            threshold=0.80,
            fail_below_threshold=True
        )

        print(f"\n[Loop] Fidelity: {result['fidelity_percent']:.2f}% ({result['exported_count']}/{result['source_count']})")

        assert result['missing_attributes'] == [], \
            f"InstrumentationLoopFunction has missing attributes: {result['missing_attributes']}"
        assert result['status'] == "PASS", \
            f"InstrumentationLoopFunction fidelity {result['fidelity_percent']}% below 80% threshold"
