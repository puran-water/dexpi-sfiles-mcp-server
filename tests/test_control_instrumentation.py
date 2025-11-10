"""
Test control and instrumentation handling in SFILES conversion.

Tests that control units (FC, LC, TC, PC) are properly converted to
ProcessInstrumentationFunction objects instead of equipment.
"""

import pytest
from src.core.conversion import get_engine, SfilesUnit, SfilesStream, SfilesModel


class TestControlInstrumentation:
    """Test control/instrumentation conversion."""

    def test_control_unit_detection_by_unit_type(self):
        """Test that unit_type='Control' is detected as control."""
        engine = get_engine()

        # Create model with control unit
        model = SfilesModel(
            units=[
                SfilesUnit(
                    name="P-101",
                    unit_type="pump_centrifugal",
                    parameters={}
                ),
                SfilesUnit(
                    name="FC-101",
                    unit_type="Control",
                    parameters={"unit_type": "Control", "control_type": "FC"}
                )
            ],
            streams=[
                SfilesStream(
                    from_unit="P-101",
                    to_unit="FC-101",
                    stream_name="signal1",
                    properties={}
                )
            ],
            model_type="PFD"
        )

        # Convert to DEXPI
        dexpi_model = engine.sfiles_to_dexpi(model)

        # Should have 1 equipment (pump), 1 instrumentation (control)
        assert len(list(dexpi_model.conceptualModel.taggedPlantItems or [])) == 1
        assert len(list(dexpi_model.conceptualModel.processInstrumentationFunctions or [])) == 1

        # Check instrumentation details
        pif = dexpi_model.conceptualModel.processInstrumentationFunctions[0]
        # Tag is composed of: category + modifier + number
        tag = f"{pif.processInstrumentationFunctionCategory}{pif.processInstrumentationFunctionModifier}-{pif.processInstrumentationFunctionNumber}"
        assert tag == "FC-101"

    def test_control_unit_detection_by_name_prefix(self):
        """Test that FC-, LC-, TC-, PC- prefixes are detected as control."""
        engine = get_engine()

        for prefix in ["FC-", "LC-", "TC-", "PC-"]:
            model = SfilesModel(
                units=[
                    SfilesUnit(
                        name="T-101",
                        unit_type="tank",
                        parameters={}
                    ),
                    SfilesUnit(
                        name=f"{prefix}101",
                        unit_type="Control",  # Still need this for now
                        parameters={"control_type": prefix.rstrip("-")}
                    )
                ],
                streams=[
                    SfilesStream(
                        from_unit="T-101",
                        to_unit=f"{prefix}101",
                        stream_name="signal",
                        properties={}
                    )
                ],
                model_type="PFD"
            )

            dexpi_model = engine.sfiles_to_dexpi(model)

            # Should have equipment and instrumentation
            assert len(list(dexpi_model.conceptualModel.taggedPlantItems or [])) == 1
            assert len(list(dexpi_model.conceptualModel.processInstrumentationFunctions or [])) == 1

    def test_mixed_equipment_and_control(self):
        """Test model with both equipment and control units."""
        engine = get_engine()

        model = SfilesModel(
            units=[
                SfilesUnit(name="TK-101", unit_type="tank", parameters={}),
                SfilesUnit(name="P-101", unit_type="pump_centrifugal", parameters={}),
                SfilesUnit(name="LC-101", unit_type="Control",
                          parameters={"unit_type": "Control", "control_type": "LC"}),
                SfilesUnit(name="FC-101", unit_type="Control",
                          parameters={"unit_type": "Control", "control_type": "FC"})
            ],
            streams=[
                SfilesStream(from_unit="TK-101", to_unit="P-101", stream_name="s1", properties={}),
                SfilesStream(from_unit="TK-101", to_unit="LC-101", stream_name="s2", properties={}),
                SfilesStream(from_unit="P-101", to_unit="FC-101", stream_name="s3", properties={})
            ],
            model_type="PFD"
        )

        dexpi_model = engine.sfiles_to_dexpi(model)

        # Should have 2 equipment (tank, pump), 2 instrumentation (LC, FC)
        assert len(list(dexpi_model.conceptualModel.taggedPlantItems or [])) == 2
        assert len(list(dexpi_model.conceptualModel.processInstrumentationFunctions or [])) == 2

        # Check equipment tags
        equipment_tags = [e.tagName for e in dexpi_model.conceptualModel.taggedPlantItems]
        assert "TK-101" in equipment_tags
        assert "P-101" in equipment_tags

        # Check instrumentation tags
        instr_tags = [
            f"{i.processInstrumentationFunctionCategory}{i.processInstrumentationFunctionModifier}-{i.processInstrumentationFunctionNumber}"
            for i in dexpi_model.conceptualModel.processInstrumentationFunctions
        ]
        assert "LC-101" in instr_tags
        assert "FC-101" in instr_tags

    def test_control_without_connected_equipment(self):
        """Test control unit without connected equipment (edge case)."""
        engine = get_engine()

        model = SfilesModel(
            units=[
                SfilesUnit(
                    name="FC-101",
                    unit_type="Control",
                    parameters={"unit_type": "Control", "control_type": "FC"}
                )
            ],
            streams=[],
            model_type="PFD"
        )

        # Should not raise - just create instrumentation without connection
        dexpi_model = engine.sfiles_to_dexpi(model)

        assert len(list(dexpi_model.conceptualModel.taggedPlantItems or [])) == 0
        assert len(list(dexpi_model.conceptualModel.processInstrumentationFunctions or [])) == 1

    def test_sensor_attached_to_instrumentation(self):
        """Test that sensor is properly attached to instrumentation."""
        engine = get_engine()

        model = SfilesModel(
            units=[
                SfilesUnit(name="P-101", unit_type="pump_centrifugal", parameters={}),
                SfilesUnit(
                    name="FC-101",
                    unit_type="Control",
                    parameters={"unit_type": "Control", "control_type": "FC"}
                )
            ],
            streams=[
                SfilesStream(from_unit="P-101", to_unit="FC-101", stream_name="signal1", properties={})
            ],
            model_type="PFD"
        )

        dexpi_model = engine.sfiles_to_dexpi(model)

        # Get the instrumentation
        pif = dexpi_model.conceptualModel.processInstrumentationFunctions[0]

        # Verify sensor is attached
        assert pif.processSignalGeneratingFunctions is not None
        assert len(pif.processSignalGeneratingFunctions) == 1

        # Verify sensor has correct type
        sensor = pif.processSignalGeneratingFunctions[0]
        assert sensor.sensorType == "Flow"

        # Verify sensing location is set
        assert sensor.sensingLocation is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
