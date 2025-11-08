"""BFD-specific tools for planning and BFD-to-PFD expansion.

This module provides tools that are genuinely BFD-specific (not thin wrappers).
Following Codex Review #6 minimal approach: avoid 'pure indirection' by only
creating tools with unique logic.

Architecture Decision (Codex Review #6):
    "Limit new tools to just bfd_to_pfd_plan. Move validation to existing SFILES tools."

BFD→PFD→P&ID Expansion Pipeline (Codex Review #7):
    The expansion process follows a structured metadata enrichment pattern:

    1. **BFD Level (Conceptual)**:
       - Blocks have process types (e.g., "Aeration Tank")
       - Ports use BfdPortSpec with BFD-level metadata
       - Streams have stream_type (material, energy, information)
       - All metadata persists to NetworkX graph

    2. **BFD→PFD Expansion** (this tool):
       - Maps BFD process types to PFD equipment configurations
       - Returns expansion options (equipment types, counts, configurations)
       - Future: Populate BfdPortSpec.canonical field with PortSpec during instantiation

    3. **PFD Level (Process Design)**:
       - Equipment with typed nozzles/ports
       - BfdPortSpec.canonical becomes populated with DEXPI NumberOfPortsClassification
       - Piping classes and nominal sizes added

    4. **PFD→P&ID Expansion**:
       - DEXPI PortSpec used to generate nozzles with full classifications
       - ISA S5.1 instrumentation tags added
       - Detailed P&ID symbols instantiated

    Key Design Pattern:
        BfdPortSpec wraps (not forks) PortSpec via optional 'canonical' field.
        This preserves BFD simplicity while maintaining a structured path to
        canonical DEXPI data for downstream expansion.
"""

import json
import logging
from typing import Any, Dict, List
from pathlib import Path

from mcp import Tool
from ..utils.response import success_response, error_response
from ..utils.process_resolver import load_process_hierarchy

logger = logging.getLogger(__name__)


class BfdTools:
    """Handles BFD-specific MCP tools."""

    def __init__(self, flowsheet_store: Dict[str, Any]):
        """Initialize with reference to flowsheet store."""
        self.flowsheets = flowsheet_store

    def get_tools(self) -> List[Tool]:
        """Return all BFD-specific tools."""
        return [
            Tool(
                name="bfd_to_pfd_plan",
                description=(
                    "Generate PFD expansion options for a BFD block. "
                    "Suggests equipment breakdowns based on process type. "
                    "Returns multiple expansion options with typical configurations."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flowsheet_id": {
                            "type": "string",
                            "description": "ID of BFD flowsheet"
                        },
                        "bfd_block": {
                            "type": "string",
                            "description": "BFD block ID to expand"
                        },
                        "include_alternates": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include alternate equipment configurations"
                        }
                    },
                    "required": ["flowsheet_id", "bfd_block"]
                }
            )
        ]

    async def execute(self, tool_name: str, args: dict) -> dict:
        """Execute BFD-specific tool."""
        if tool_name == "bfd_to_pfd_plan":
            return await self._bfd_to_pfd_plan(args)
        else:
            return error_response(f"Unknown BFD tool: {tool_name}")

    async def _bfd_to_pfd_plan(self, args: dict) -> dict:
        """Generate PFD expansion plan for a BFD block.

        This tool provides intelligent suggestions for breaking down
        high-level BFD process blocks into detailed PFD equipment.

        Args:
            flowsheet_id: ID of BFD flowsheet
            bfd_block: BFD block ID to expand
            include_alternates: Include alternate configurations

        Returns:
            Expansion plan with multiple PFD equipment options
        """
        flowsheet_id = args["flowsheet_id"]
        bfd_block = args["bfd_block"]
        include_alternates = args.get("include_alternates", True)

        # Validate flowsheet exists
        if flowsheet_id not in self.flowsheets:
            return error_response(f"Flowsheet {flowsheet_id} not found")

        flowsheet = self.flowsheets[flowsheet_id]

        # Validate it's a BFD
        if not hasattr(flowsheet, 'type') or flowsheet.type != "BFD":
            return error_response(
                f"Flowsheet {flowsheet_id} is not a BFD. "
                "BFD-to-PFD planning only works with BFD flowsheets."
            )

        # Validate block exists
        if bfd_block not in flowsheet.state.nodes:
            available_blocks = list(flowsheet.state.nodes.keys())
            return error_response(
                f"Block {bfd_block} not found in flowsheet. "
                f"Available blocks: {', '.join(available_blocks)}"
            )

        # Get block metadata
        block_data = flowsheet.state.nodes[bfd_block]
        process_type = block_data.get('unit_type', 'Unknown')
        category = block_data.get('category', '')
        subcategory = block_data.get('subcategory', '')

        # Generate expansion options based on process type
        expansion_plan = self._generate_expansion_options(
            process_type=process_type,
            category=category,
            subcategory=subcategory,
            include_alternates=include_alternates
        )

        # Add BFD block context
        expansion_plan["bfd_block"] = bfd_block
        expansion_plan["bfd_block_metadata"] = {
            "process_type": process_type,
            "category": category,
            "subcategory": subcategory,
            "equipment_tag": block_data.get('equipment_tag', ''),
            "area_number": block_data.get('area_number', '')
        }

        return success_response(expansion_plan)

    def _generate_expansion_options(
        self,
        process_type: str,
        category: str,
        subcategory: str,
        include_alternates: bool
    ) -> dict:
        """Generate PFD expansion options for a process type.

        This is the core intelligence of BFD-to-PFD planning.
        Maps high-level process types to typical equipment configurations.

        Args:
            process_type: BFD process type (e.g., "Primary Clarification")
            category: Process category (e.g., "Primary Treatment")
            subcategory: Process subcategory
            include_alternates: Include alternate configurations

        Returns:
            Dictionary with expansion options
        """
        # Load process hierarchy for context
        hierarchy = load_process_hierarchy()

        # Define expansion rules based on process type
        # This mapping represents typical wastewater treatment equipment breakdowns
        expansion_rules = self._get_expansion_rules()

        # Find matching rule
        options = []
        recommended_idx = None

        if process_type in expansion_rules:
            rule = expansion_rules[process_type]
            options = rule["options"]
            recommended_idx = rule.get("recommended", 0)
        else:
            # Generic fallback based on category
            options = self._generate_generic_options(category, subcategory)

        # Filter alternates if requested
        if not include_alternates and len(options) > 1:
            if recommended_idx is not None:
                options = [options[recommended_idx]]
            else:
                options = [options[0]]

        return {
            "process_type": process_type,
            "category": category,
            "subcategory": subcategory,
            "pfd_options": options,
            "recommended_option": recommended_idx if include_alternates else 0
        }

    def _get_expansion_rules(self) -> dict:
        """Define BFD-to-PFD expansion rules for wastewater treatment.

        Returns dictionary mapping process types to typical equipment.
        Each rule includes multiple configuration options.
        """
        return {
            # Primary Treatment
            "Primary Clarification": {
                "options": [
                    {
                        "equipment_type": "clarifier",
                        "description": "Circular primary clarifier with mechanical sludge removal",
                        "typical_count": 2,
                        "configuration": "parallel",
                        "additional_equipment": ["pump", "valve", "flow_meter"]
                    },
                    {
                        "equipment_type": "clarifier",
                        "description": "Rectangular primary clarifier with chain-and-flight",
                        "typical_count": 2,
                        "configuration": "parallel",
                        "additional_equipment": ["pump", "valve", "flow_meter"]
                    }
                ],
                "recommended": 0
            },

            # Secondary Treatment
            "Aeration Tank": {
                "options": [
                    {
                        "equipment_type": "reactor",
                        "description": "Activated sludge basin with fine-bubble diffusers",
                        "typical_count": 4,
                        "configuration": "series-parallel",
                        "additional_equipment": ["blower", "mixer", "do_sensor"]
                    },
                    {
                        "equipment_type": "reactor",
                        "description": "Oxidation ditch with mechanical aerators",
                        "typical_count": 2,
                        "configuration": "parallel",
                        "additional_equipment": ["aerator", "do_sensor"]
                    }
                ],
                "recommended": 0
            },

            "Secondary Clarification": {
                "options": [
                    {
                        "equipment_type": "clarifier",
                        "description": "Circular secondary clarifier with RAS/WAS pumps",
                        "typical_count": 3,
                        "configuration": "parallel",
                        "additional_equipment": ["pump", "pump", "valve", "level_sensor"]
                    }
                ],
                "recommended": 0
            },

            # Tertiary Treatment
            "Filtration": {
                "options": [
                    {
                        "equipment_type": "filter",
                        "description": "Rapid sand filters with backwash system",
                        "typical_count": 4,
                        "configuration": "parallel",
                        "additional_equipment": ["pump", "valve", "pressure_sensor"]
                    },
                    {
                        "equipment_type": "filter",
                        "description": "Membrane filtration (MF/UF)",
                        "typical_count": 3,
                        "configuration": "parallel",
                        "additional_equipment": ["pump", "valve", "transmembrane_pressure_sensor"]
                    }
                ],
                "recommended": 0
            },

            "Disinfection": {
                "options": [
                    {
                        "equipment_type": "reactor",
                        "description": "UV disinfection channels with UV lamps",
                        "typical_count": 2,
                        "configuration": "parallel",
                        "additional_equipment": ["uv_sensor", "flow_meter"]
                    },
                    {
                        "equipment_type": "reactor",
                        "description": "Chlorine contact basin with dosing system",
                        "typical_count": 2,
                        "configuration": "series",
                        "additional_equipment": ["pump", "chlorine_analyzer", "mixer"]
                    }
                ],
                "recommended": 0
            },

            # Solids Treatment
            "Thickening": {
                "options": [
                    {
                        "equipment_type": "thickener",
                        "description": "Gravity belt thickener",
                        "typical_count": 2,
                        "configuration": "parallel",
                        "additional_equipment": ["pump", "polymer_dosing_system"]
                    },
                    {
                        "equipment_type": "thickener",
                        "description": "Dissolved air flotation (DAF) thickener",
                        "typical_count": 1,
                        "configuration": "single",
                        "additional_equipment": ["compressor", "pump", "polymer_dosing_system"]
                    }
                ],
                "recommended": 0
            },

            "Anaerobic Digestion": {
                "options": [
                    {
                        "equipment_type": "reactor",
                        "description": "Mesophilic anaerobic digesters with gas handling",
                        "typical_count": 2,
                        "configuration": "series",
                        "additional_equipment": ["heat_exchanger", "mixer", "pump", "gas_meter", "temperature_sensor"]
                    }
                ],
                "recommended": 0
            },

            "Dewatering": {
                "options": [
                    {
                        "equipment_type": "centrifuge",
                        "description": "Decanter centrifuge with polymer conditioning",
                        "typical_count": 2,
                        "configuration": "parallel",
                        "additional_equipment": ["pump", "polymer_dosing_system", "conveyor"]
                    },
                    {
                        "equipment_type": "filter_press",
                        "description": "Belt filter press with polymer conditioning",
                        "typical_count": 2,
                        "configuration": "parallel",
                        "additional_equipment": ["pump", "polymer_dosing_system", "conveyor"]
                    }
                ],
                "recommended": 0
            }
        }

    def _generate_generic_options(self, category: str, subcategory: str) -> List[dict]:
        """Generate generic expansion options for unknown process types.

        Args:
            category: Process category
            subcategory: Process subcategory

        Returns:
            List of generic expansion options
        """
        # Provide category-based defaults
        if "Primary" in category:
            return [
                {
                    "equipment_type": "tank",
                    "description": f"Generic primary treatment tank for {subcategory}",
                    "typical_count": 2,
                    "configuration": "parallel",
                    "additional_equipment": ["pump", "valve"]
                }
            ]
        elif "Secondary" in category:
            return [
                {
                    "equipment_type": "reactor",
                    "description": f"Generic biological reactor for {subcategory}",
                    "typical_count": 2,
                    "configuration": "series",
                    "additional_equipment": ["pump", "mixer", "sensor"]
                }
            ]
        elif "Tertiary" in category or "Advanced" in category:
            return [
                {
                    "equipment_type": "filter",
                    "description": f"Generic tertiary treatment unit for {subcategory}",
                    "typical_count": 3,
                    "configuration": "parallel",
                    "additional_equipment": ["pump", "valve"]
                }
            ]
        elif "Solids" in category or "Sludge" in category:
            return [
                {
                    "equipment_type": "processor",
                    "description": f"Generic solids handling equipment for {subcategory}",
                    "typical_count": 2,
                    "configuration": "parallel",
                    "additional_equipment": ["pump", "conveyor"]
                }
            ]
        else:
            # Ultimate fallback
            return [
                {
                    "equipment_type": "unit",
                    "description": f"Generic process unit for {category}/{subcategory}",
                    "typical_count": 1,
                    "configuration": "single",
                    "additional_equipment": []
                }
            ]


__all__ = ["BfdTools"]
