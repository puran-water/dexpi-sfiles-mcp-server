# High-ROI MCP Tools Implementation Plan for Engineering Drawing Generation

## Executive Summary

After extensive analysis of pyDEXPI/SFILES2 capabilities and our existing MCP server, this plan outlines a **phased consolidation from 47 tools to 12 powerful tools** that will dramatically improve LLM generation quality for engineering drawings. The focus is on reducing tool calls from ~50-200 to 1-3 per operation while preventing common LLM errors.

**Revised Strategy: Staged deployment with compatibility window, not hard cut-over.**

**Critical Path (Days 1-3):**
1. Fix broken imports and syntax errors
2. Implement thin transaction layer (3 tools)
3. Add minimal `rules_apply` for validation loop
4. Basic `graph_connect` autowiring
5. Enable resource notifications

This delivers immediate value while maintaining all 47 existing tools.

## Current State Analysis

### What We Have
- **47 low-level tools** requiring many sequential calls
- Basic DEXPI/SFILES operations (add equipment, piping, etc.)
- Git-based persistence with ProjectPersistence
- Validation through ValidationTools
- Schema introspection via DexpiIntrospector
- Graph analytics and search capabilities
- Standardized response format (success_response, error_response)

### What pyDEXPI/SFILES2 Provide (To Leverage)
- **pyDEXPI:**
  - DexpiPattern for reusable subgraphs
  - piping_toolkit for connections (connect_piping_network_segment, insert_item_to_segment)
  - model_toolkit for merging (combine_dexpi_models, import_model_contents_into_model)
  - MLGraphLoader for validation
  - SyntheticPIDGenerator for pattern-based generation
  - Unique ID generation via DexpiBaseModel

- **SFILES2:**
  - Flowsheet class with add_unit/add_stream
  - Heat integration node merging
  - Control instrumentation with v2 tagging
  - NetworkX graph as internal state

### Critical Gaps Identified
- **No transaction/rollback capability** → Partial edits, brittle sequences
- **No parametric templates** → High friction for repeated areas
- **No batch operations** → Cognitive load remains high for LLMs
- **No autowiring with rules** → Dangling/mismatched ports
- **No automatic tag generation** → Inconsistent tags
- **No business rule engine with autofix** → No generate→validate→autofix loop
- **No notifications** → UIs won't refresh after changes
- **Import errors** → `Flowsheet_Class` vs `pyflowsheet`, missing `rapidfuzz`

## Tool Consolidation Strategy (Revised)

### Staged Migration: 47 Tools → 12 Tools

**New Approach:** Implement 12 powerful tools alongside existing 47, with staged deprecation:
1. **Days 1-3:** Add transaction layer + critical tools (maintains all 47 tools)
2. **Week 1:** Full 12-tool implementation behind feature flag
3. **Week 2:** Compatibility testing with coverage matrix
4. **Week 3:** Deprecate 47 tools after validation

#### The 12 Core Tools

1. **Model Management (3 tools)**
   - `model_create` - Initialize any model type (replaces dexpi_create_pid, sfiles_create_flowsheet)
   - `model_load` - Load from any source (replaces project_load, all import tools)
   - `model_save` - Save to any format (replaces project_save, all export tools)

2. **Transactional Operations (3 tools)**
   - `model_tx_begin` - Start transaction for atomic operations
   - `model_tx_apply` - Apply ANY operation atomically (replaces ALL add_* and connect_* tools)
   - `model_tx_commit` - Commit or rollback transaction

3. **High-Level Construction (3 tools)**
   - `area_deploy` - Deploy templates with parameters (replaces all individual creation tools)
   - `graph_connect` - Smart autowiring with rules (replaces all connection tools)
   - `graph_modify` - Inline modifications, splits, merges (replaces insert/modify tools)

4. **Intelligence (3 tools)**
   - `rules_apply` - Validation + autofix (replaces all validate_* tools)
   - `schema_query` - Universal schema introspection (replaces all schema_* tools)
   - `search_execute` - Universal search with any criteria (replaces all search_* tools)

### Tools Being Replaced

**Eliminated by `model_tx_apply` + `area_deploy` (25 tools):**
- All dexpi_add_* tools (equipment, piping, valve, instrumentation, control_loop)
- All sfiles_add_* tools (unit, stream, control)
- All individual creation and connection tools
- dexpi_connect_components, dexpi_insert_valve_in_segment

**Eliminated by `model_create/load/save` (12 tools):**
- dexpi_create_pid, sfiles_create_flowsheet
- All import tools (dexpi_import_json, dexpi_import_proteus_xml, sfiles_from_string)
- All export tools (dexpi_export_json, dexpi_export_graphml, sfiles_to_string, etc.)
- All project_* tools

**Eliminated by `rules_apply` (4 tools):**
- validate_model, validate_round_trip
- sfiles_parse_and_validate, sfiles_canonical_form

**Eliminated by unified tools (6 tools):**
- All schema_* tools → `schema_query`
- All search_* tools → `search_execute`
- All graph_* analysis tools → built into new graph tools

## Implementation Phases (Revised for Immediate Value)

### Phase 0: Critical Fixes & Minimal Viable Tools (Days 1-3)
**Objective: Fix breaks, deliver immediate value without disruption**

#### Day 1: Fix Import & Syntax Issues
1. **Code Fixes:**
   - Fix `tools/sfiles_tools.py` stray import and docstring
   - Replace `Flowsheet_Class.flowsheet` with correct package
   - Add `rapidfuzz` to requirements.txt (not `fuzzywuzzy`)
   - Add `compileall` to CI for syntax checking
   - Consolidate to single `.mcp.json` manifest

2. **Dependency Validation:**
   - Verify pyDEXPI version and GraphML dependencies
   - Test all imports in clean environment

#### Days 2-3: Thin Transaction Layer
**Implementation: Minimal copy-on-write transactions**
```python
# Simple transaction manager wrapping existing tools
class TransactionManager:
    def begin(self, model_id: str) -> str:
        """Deep copy model, return tx_id"""
        
    def apply(self, tx_id: str, operations: List[Dict]) -> Dict:
        """Dispatch to existing 47 tools, track diff"""
        # Operations like: {"tool": "dexpi_add_equipment", "params": {...}}
        
    def commit(self, tx_id: str) -> Dict:
        """Swap working copy to main store, emit notification"""
```

**MCP Tools Added:**
- `model_tx_begin` - Start transaction
- `model_tx_apply` - Batch operations via existing tools
- `model_tx_commit` - Commit with notifications

#### Day 3: Minimal Rules & Autowiring
1. **Minimal `rules_apply`:**
```python
def rules_apply(model_id: str, rule_sets: List[str], autofix: bool = False):
    # Wrap existing validators
    # Return: {"issues": [...], "can_autofix": false}
```

2. **Basic `graph_connect`:**
```python
def graph_connect(model_id: str, strategy: str = "by_port_type", rules: Dict):
    # Use pydexpi.toolkits.piping_toolkit
    # Connect N pumps to header with optional valve insertion
```

3. **Enable Notifications:**
   - After `model_tx_commit`, emit resource change notification
   - Allows MCP clients to refresh

### Phase 1: Complete Transaction System & Area Templates (Days 4-7)
**Builds on Phase 0 foundation**

#### 1.1 Enhanced Transaction Manager
```python
# src/managers/transaction_manager.py
class TransactionManager:
    """Atomic operations for DEXPI/SFILES models."""
    
    def __init__(self, model_stores):
        self.dexpi_models = model_stores['dexpi']
        self.flowsheets = model_stores['sfiles']
        self.transactions = {}  # tx_id -> TransactionState
        
    def begin(self, model_id: str, model_type: str = "auto") -> str:
        """Start transaction by deep copying model."""
        import copy
        import uuid
        
        tx_id = str(uuid.uuid4())
        
        # Deep copy the model
        if model_type == "dexpi":
            original = self.dexpi_models[model_id]
            clone = copy.deepcopy(original)
        else:  # sfiles
            original = self.flowsheets[model_id]
            clone = Flowsheet()
            clone.state = copy.deepcopy(original.state)
            
        self.transactions[tx_id] = {
            'model_id': model_id,
            'model_type': model_type,
            'original': original,
            'working': clone,
            'operations': [],
            'status': 'active'
        }
        
        return tx_id
    
    def apply_batch(self, tx_id: str, operations: List[Dict]) -> Dict:
        """Apply operations to transaction model."""
        tx = self.transactions[tx_id]
        results = []
        
        for op in operations:
            try:
                result = self._apply_operation(tx['working'], op)
                results.append({"op": op, "result": result, "ok": True})
                tx['operations'].append(op)
            except Exception as e:
                results.append({"op": op, "error": str(e), "ok": False})
                # Stop on first error
                break
        
        # Calculate diff
        diff = self._calculate_diff(tx['original'], tx['working'])
        
        return {
            "ok": all(r["ok"] for r in results),
            "results": results,
            "diff": diff,
            "tx_id": tx_id
        }
    
    def commit(self, tx_id: str) -> Dict:
        """Replace original with transaction model."""
        tx = self.transactions[tx_id]
        
        # Replace in store
        if tx['model_type'] == 'dexpi':
            self.dexpi_models[tx['model_id']] = tx['working']
        else:
            self.flowsheets[tx['model_id']] = tx['working']
        
        # Clean up
        tx['status'] = 'committed'
        del self.transactions[tx_id]
        
        return {"ok": True, "operations_applied": len(tx['operations'])}
    
    def rollback(self, tx_id: str) -> Dict:
        """Discard transaction."""
        tx = self.transactions[tx_id]
        tx['status'] = 'rolled_back'
        del self.transactions[tx_id]
        return {"ok": True, "operations_discarded": len(tx['operations'])}
```

#### 1.2 Batch Operation Tools
```python
# MCP Tools to add:
- model_tx_begin: Start transaction
- model_tx_apply: Apply batch operations  
- model_tx_commit: Commit changes
- model_tx_rollback: Discard changes
- model_batch_add: Add multiple components in one call
```

### Phase 2: Templates, Autowiring & Rule Repository (Week 2)
**ROI: One call creates entire pump station, prevents errors**

**Key Sequencing Change:** Autowiring before full template library for quick wins

#### 2.1 Template System (Extending pyDEXPI DexpiPattern)
```python
# src/templates/parametric_template.py
from pydexpi.syndata.dexpi_pattern import DexpiPattern
from pydexpi.syndata.basic_connectors import BasicPipingInConnector, BasicPipingOutConnector

class ParametricTemplate(DexpiPattern):
    """Parametric template extending pyDEXPI's DexpiPattern."""
    
    def __init__(self, template_def: Dict):
        # Initialize base pattern
        super().__init__(template_def['base_model'], template_def['label'])
        
        # Add parameter schema
        self.param_schema = template_def['parameters']
        self.default_params = template_def['defaults']
        self.anchor_schema = template_def['anchors']
        
    def instantiate(self, params: Dict, anchors: Dict, target_model) -> Dict:
        """Instantiate template with parameters."""
        # Validate parameters
        validated_params = self._validate_params(params)
        
        # Apply parameters to base model
        instantiated_model = self._apply_parameters(validated_params)
        
        # Use pyDEXPI's incorporate_pattern
        for anchor_name, target_connector in anchors.items():
            own_connector = self.connectors[anchor_name]
            target_model.incorporate_pattern(
                own_connector, 
                instantiated_model, 
                target_connector
            )
        
        # Auto-tag based on parameters
        self._apply_tagging_scheme(instantiated_model, validated_params)
        
        return instantiated_model
```

#### 2.2 Template Library
```python
# src/templates/library/pump_station.py
def create_pump_station_template() -> ParametricTemplate:
    """N+1 pump station template."""
    return ParametricTemplate({
        'label': 'pump_station_N+1',
        'parameters': {
            'service': {'type': 'string', 'required': True},
            'trains': {'type': 'integer', 'min': 2, 'max': 6},
            'redundancy': {'enum': ['N+1', 'N+2', '2x50%', '3x33%']},
            'include_suction_strainer': {'type': 'boolean', 'default': True},
            'valving': {'enum': ['isolation', 'isolation+check', 'full']},
            'control': {'enum': ['none', 'local', 'pressure_PID', 'flow_PID']}
        },
        'defaults': {
            'trains': 3,
            'redundancy': 'N+1',
            'include_suction_strainer': True,
            'valving': 'isolation+check',
            'control': 'pressure_PID'
        },
        'anchors': {
            'suction_header': BasicPipingInConnector,
            'discharge_header': BasicPipingOutConnector
        },
        'base_model': self._build_base_pump_model()
    })

# Similar templates for:
# - RO train (2-stage, 3-stage with CIP)
# - MBR system (cassettes, blowers, backpulse)
# - Tank farm (with vents, drains, instrumentation)
# - Chemical dosing skid
# - Evaporator/crystallizer
```

#### 2.3 Area Tools
```python
# MCP Tools to add:
- area_instantiate: Deploy parametric template
- area_list: List available templates
- area_describe: Get template schema
- area_capture: Convert subgraph to template
```

### Phase 3: Testing & Staged Cut-Over (Week 3)
**ROI: Safe transition with rollback path**

#### 3.1 Coverage Matrix Testing
- Map all 47 old tools to new 12-tool operations
- Verify functional parity
- Performance benchmarking

#### 3.2 Compatibility Window
- Both tool surfaces available
- Feature flag for new tools: `experimental=true`
- Monitor usage patterns

#### 3.3 Deprecation Schedule
- Week 3 Day 3: Mark old tools deprecated
- Week 3 Day 4: Final validation
- Week 3 Day 5: Remove old tools (if all tests green)

#### 3.1 AutoWirer (Leveraging piping_toolkit)
```python
# src/managers/autowirer.py
from pydexpi.toolkits import piping_toolkit as pt

class SmartAutoWirer:
    """Intelligent connection management."""
    
    def find_open_ports(self, model, filter_criteria=None) -> List[Dict]:
        """Find unconnected nozzles/ports."""
        open_ports = []
        
        for equipment in model.conceptualModel.taggedPlantItems:
            if hasattr(equipment, 'nozzles'):
                for nozzle in equipment.nozzles:
                    if not self._is_connected(nozzle):
                        if self._matches_filter(nozzle, filter_criteria):
                            open_ports.append({
                                'equipment': equipment.tagName,
                                'nozzle': nozzle.subTagName,
                                'type': nozzle.nozzleType,
                                'id': nozzle.id
                            })
        
        return open_ports
    
    def autowire(self, model, strategy: str, rules: Dict) -> Dict:
        """Smart connection with rules."""
        connections_made = []
        
        if strategy == "by_port_type":
            # Find matching ports
            sources = self._find_ports_by_type(model, rules['from_type'])
            target = self._find_node(model, rules['to_anchor'])
            
            for source in sources:
                # Create piping segment
                segment = self._create_segment_with_components(
                    rules.get('insert', []),
                    rules.get('line_class', 'CS150')
                )
                
                # Use pyDEXPI's connect_piping_network_segment
                pt.connect_piping_network_segment(
                    segment,
                    source['nozzle'],
                    as_source=True
                )
                pt.connect_piping_network_segment(
                    segment,
                    target,
                    as_source=False
                )
                
                connections_made.append({
                    'from': source['equipment'],
                    'to': rules['to_anchor'],
                    'segment': segment.id
                })
        
        return {
            "ok": True,
            "connections": connections_made,
            "count": len(connections_made)
        }
    
    def insert_inline(self, model, edge_id: str, components: List[str]) -> Dict:
        """Insert components inline using piping_toolkit."""
        segment = self._find_segment(model, edge_id)
        
        for component_type in components:
            component = self._create_component(component_type)
            # Use pyDEXPI's insert_item_to_segment
            pt.insert_item_to_segment(
                segment,
                position=len(segment.items) // 2,  # Middle
                item=component,
                connection=self._create_connection()
            )
        
        return {"ok": True, "components_inserted": len(components)}
```

#### 3.2 Autowiring Tools
```python
# MCP Tools to add:
- graph_find_open_ports: Identify unconnected nozzles
- graph_autowire: Smart connection with rules
- graph_insert_inline: Add valves/instruments to existing pipes
```

## Key Architecture Decisions (Revised)

### 1. Staged Migration, Not Hard Cut-Over
- **Compatibility window** with both tool surfaces
- **Feature flags** for gradual activation
- **Coverage matrix** ensuring no functionality lost
- **Rollback path** if issues discovered

### 2. Transaction-First, But Thin Layer Initially
- Start with simple copy-on-write
- Dispatch to existing tools
- Add diff tracking and rollback
- Gradually move logic into transaction manager

### 3. Pull Critical Tools Forward
- **`rules_apply` in Phase 0** (minimal version)
- **`graph_connect` in Phase 0** (basic autowiring)
- **Notifications immediately** (not Week 3)
- Templates can wait if autowiring works

### 4. Idempotency & Determinism Built-In
- All mutating tools accept `idempotency_key`
- Return stable IDs for retry safety
- Use canonical JSON with sorted keys
- Deterministic tag generation

#### 4.1 Rule Engine (Extending MLGraphLoader)
```python
# src/rules/rule_engine.py
from pydexpi.loaders.ml_graph_loader import MLGraphLoader

class RuleEngine(MLGraphLoader):
    """Business rules extending pyDEXPI validation."""
    
    def __init__(self):
        super().__init__()
        self.rule_repository = {}
        
    def apply_rule(self, model, rule_id: str, autofix: bool = False) -> Dict:
        """Apply rule with optional autofix."""
        rule = self.rule_repository[rule_id]
        
        # Convert to graph using parent's method
        graph = self.dexpi_to_graph(model)
        
        # Run assertions
        violations = []
        for assertion in rule['assertions']:
            if not self._check_assertion(graph, assertion):
                violations.append({
                    'assertion': assertion,
                    'severity': rule['severity'],
                    'message': assertion.get('message', 'Rule violation')
                })
        
        # Apply autofix if requested
        fixes_applied = []
        if autofix and violations and rule.get('autofix'):
            for patch_op in rule['autofix']['patch']:
                self._apply_patch_operation(model, patch_op)
                fixes_applied.append(patch_op)
        
        return {
            "ok": len(violations) == 0,
            "violations": violations,
            "fixes_applied": fixes_applied
        }
    
    def from_natural_language(self, text: str, context: Dict) -> Dict:
        """Convert natural language to rule (draft only)."""
        # This would use an LLM to parse the text
        # For now, return a template
        return {
            "draft_rule": {
                "id": f"draft_{hash(text)[:8]}",
                "title": "Generated from: " + text[:50],
                "severity": "warning",
                "applies_to": context.get("selector", {}),
                "assertions": [],
                "autofix": {
                    "strategy": "safe_insert",
                    "patch": []
                }
            },
            "confidence": 0.7,
            "requires_review": True
        }
```

#### 4.2 Rule Repository
```python
# src/rules/repository.py
class RuleRepository:
    """Versioned rule storage."""
    
    def commit_rule(self, rule: Dict, message: str) -> Dict:
        """Commit rule to repository."""
        # Validate rule schema
        validated = self._validate_rule_schema(rule)
        
        # Add version info
        validated['version'] = self._next_version(validated['id'])
        validated['committed_at'] = datetime.now().isoformat()
        validated['commit_message'] = message
        
        # Store in git-backed repository
        self._store_rule(validated)
        
        return {"ok": True, "rule_id": validated['id'], "version": validated['version']}
```

#### 4.3 Predefined Rules
```python
# src/rules/library/pump_station_rules.py
PUMP_STATION_MINIMUMS = {
    "id": "pump_station_minimums",
    "title": "Pump station minimum requirements",
    "severity": "error",
    "applies_to": {
        "selector": {"type": "centrifugal_pump"},
        "within_area": "PumpStation*"
    },
    "assertions": [
        {
            "kind": "exists_upstream",
            "of": "{pump}",
            "component_type": "suction_strainer",
            "distance_max": 1
        },
        {
            "kind": "exists_inline",
            "on_edge": "{pump}->*",
            "component_type": "check_valve"
        },
        {
            "kind": "exists_inline", 
            "on_edge": "{pump}->*",
            "component_type": "isolation_valve"
        }
    ],
    "autofix": {
        "strategy": "safe_insert",
        "patch": [
            {"op": "insert_upstream", "target": "{pump}", "type": "strainer"},
            {"op": "insert_inline", "edge": "{pump}->*", "type": "check_valve"},
            {"op": "insert_inline", "edge": "{pump}->*", "type": "gate_valve"}
        ]
    }
}
```

#### 4.4 Rule Tools
```python
# MCP Tools to add:
- rules_apply: Apply rule with autofix
- rules_commit: Add rule to repository
- rules_from_nl: Parse natural language to rule
- rules_test: Test rule on models
- rules_capture: Learn from fixes
```

## Acceptance Criteria for Phase 0 (Days 1-3)

**Must Complete:**
1. ✓ All imports work, no syntax errors
2. ✓ `model_tx_*` tools functional with existing 47 tools
3. ✓ `rules_apply` returns structured issues (autofix=false OK)
4. ✓ `graph_connect` can wire N pumps to header with check valves
5. ✓ Resource notifications emitted after commits
6. ✓ All existing 47 tools still work

**Success Metrics:**
- Reduce 10-pump station from 50 calls to 3
- LLM can validate→fix→validate in single session
- No breaking changes to existing workflows

#### 5.1 Tag Manager
```python
# src/managers/tag_manager.py
class TagManager:
    """Automatic tag generation and management."""
    
    def __init__(self):
        self.schemes = {}
        self.reservations = {}
        
    def set_scheme(self, model_id: str, scheme: Dict) -> None:
        """Configure tagging scheme."""
        self.schemes[model_id] = {
            'prefixes': scheme['prefixes'],  # {'pump': 'P', 'valve': 'V'}
            'format': scheme['format'],  # '{prefix}-{area}{seq:03d}{suffix}'
            'areas': scheme['areas'],  # {'100': 'Feed', '200': 'RO'}
            'sequences': {}  # Track next number per prefix-area
        }
    
    def generate_tag(self, model_id: str, equipment_type: str, area: str = None) -> str:
        """Generate next tag in sequence."""
        scheme = self.schemes[model_id]
        prefix = scheme['prefixes'].get(equipment_type, 'X')
        
        # Get next sequence number
        key = f"{prefix}-{area or '000'}"
        if key not in scheme['sequences']:
            scheme['sequences'][key] = 1
        
        seq = scheme['sequences'][key]
        scheme['sequences'][key] += 1
        
        # Format tag
        tag = scheme['format'].format(
            prefix=prefix,
            area=area or '',
            seq=seq,
            suffix=''
        )
        
        return tag
    
    def reserve_tags(self, model_id: str, equipment_type: str, count: int, prefix: str = None) -> List[str]:
        """Reserve tags for N+1 patterns."""
        tags = []
        for i in range(count):
            suffix = chr(65 + i) if count > 1 else ''  # A, B, C...
            tag = self.generate_tag(model_id, equipment_type)
            if suffix:
                tag = tag + suffix
            tags.append(tag)
            
        self.reservations[model_id] = self.reservations.get(model_id, []) + tags
        return tags
```

#### 5.2 Tag Tools
```python
# MCP Tools to add:
- tag_scheme_set: Configure tagging scheme
- tag_reserve: Reserve tags for redundancy
- tag_autogenerate: Generate tags by area/type
```

## Revised Timeline

### Days 1-3: Immediate Value Delivery
- Day 1: Fix all breaks, add dependencies
- Day 2: Implement transaction layer
- Day 3: Add rules_apply, graph_connect, notifications

### Week 1 (Days 4-7): Core Infrastructure
1. **Transaction Manager** (2 days)
   - Core transaction system with deep copying
   - Unified operation dispatcher for model_tx_apply
   - Diff calculation and rollback
   
2. **Universal Model Operations** (3 days)
   - `model_create` - Unified model initialization
   - `model_load` - Universal loader for all formats
   - `model_save` - Universal saver with version control
   - Operation registry for model_tx_apply

### Week 2: High-Level Construction
1. **Template System & area_deploy** (3 days)
   - ParametricTemplate extending DexpiPattern
   - Template library (pump station, RO train, tank farm)
   - `area_deploy` tool implementation
   
2. **Smart Connection System** (2 days)
   - `graph_connect` - Rule-based autowiring
   - `graph_modify` - Inline modifications
   - Port finding and matching logic

### Week 3: Validation & Migration
1. **Unified Intelligence Tools** (2 days)
   - `rules_apply` - Comprehensive validation + autofix
   - `schema_query` - Universal schema access
   - `search_execute` - Unified search interface
   
2. **Testing & Validation** (2 days)
   - Comprehensive testing of all 12 tools
   - Performance benchmarking
   - Validation that all 47 old tool functionalities are covered
   
3. **Hard Cut-Over** (1 day)
   - Remove all 47 old tools from server.py
   - Update MCP manifest to only expose 12 tools
   - Update all documentation
   - Clean up obsolete code

## Success Metrics

### Quantitative
- **Tool count**: 47 → 12 (75% reduction)
- **Tool call reduction**: 50+ → 3 (95% reduction)
- **Error rate**: 90% reduction in tagging/connection errors
- **Generation time**: 75% reduction for standard patterns
- **Rollback capability**: 100% of operations reversible
- **Documentation size**: 75% reduction (12 tools vs 47)

### Qualitative
- LLM can create entire pump station in 1 call
- No more dangling ports or mismatched connections
- Automatic compliance with design standards
- Version-controlled rule repository
- Dramatically simplified mental model for LLMs

## Key Design Decisions

### 1. Radical Simplification via Hard Cut-Over
- **No backward compatibility** - clean break for maximum simplification
- 47 tools → 12 tools after thorough testing
- Single user (no migration concerns)
- Remove all technical debt in one sweep

### 2. Leverage pyDEXPI/SFILES2 Native Functions
- Use DexpiPattern for templates (don't reinvent)
- Use piping_toolkit for connections
- Extend MLGraphLoader for validation
- Use model_toolkit for merging

### 3. Transaction-First Architecture
- Every mutation goes through transaction
- Atomic batch operations
- Full rollback capability
- Idempotent operations via UUID tracking

### 4. Declarative Over Imperative
- Templates define structure declaratively
- Rules define requirements declaratively
- Autowiring uses declarative matching
- Tags follow declarative schemes

### 5. Universal Tools Over Specific Ones
- `model_tx_apply` handles ALL operations
- `schema_query` handles ALL schema needs
- `search_execute` handles ALL search patterns
- `rules_apply` handles ALL validation

## Gap Analysis (Current vs Target)

| Capability | Current Code | Target (12 tools) | Phase 0 Fix | Final Phase |
|------------|--------------|-------------------|-------------|-------------|
| **Tool Count** | 47 exposed | 12 tools | Keep 47, add 3 tx tools | Deprecate to 12 |
| **Transactions** | None | Full ACID | Thin copy-on-write | Full implementation |
| **Templates** | Generator not wired | area_deploy | - | Week 2 |
| **Autowiring** | None | Smart rules | Basic by-port-type | Full rules |
| **Rules** | Validators only | Autofix engine | Wrap validators | Full autofix |
| **Notifications** | Not emitted | After all changes | Add immediately | Enhanced |
| **Imports** | Broken | Working | Fix Day 1 | - |

## Risk Mitigation (Revised)

### Technical Risks
1. **pyDEXPI limitations**: Work within constraints, contribute fixes upstream
2. **Performance with large models**: Implement lazy loading, caching
3. **Complex rule interactions**: Priority system, conflict detection

### Implementation Risks
1. **Scope creep**: Strict phase boundaries, MVP first
2. **Integration issues**: Comprehensive testing at each phase
3. **Documentation lag**: Document as we build

## Appendix A: Complete Tool Specifications (The 12 Tools)

### 1. Model Management Tools
```json
{
  "model_create": {
    "description": "Create a new model of any type",
    "input": {
      "model_type": "dexpi|sfiles",
      "name": "string",
      "metadata": {
        "project": "string",
        "description": "string",
        "revision": "string"
      }
    },
    "output": {
      "ok": true,
      "model_id": "string"
    }
  },
  
  "model_load": {
    "description": "Load model from any source",
    "input": {
      "source": "project|json|xml|sfiles_string",
      "path": "string (for project/file sources)",
      "content": "string (for direct content)",
      "model_id": "string (optional, auto-generated if not provided)"
    },
    "output": {
      "ok": true,
      "model_id": "string",
      "model_type": "dexpi|sfiles",
      "statistics": {}
    }
  },
  
  "model_save": {
    "description": "Save model to any format",
    "input": {
      "model_id": "string",
      "format": "project|json|graphml|sfiles_v1|sfiles_v2",
      "path": "string (optional for project)",
      "commit_message": "string (optional for git)"
    },
    "output": {
      "ok": true,
      "content": "string (for non-project formats)",
      "path": "string (for project format)"
    }
  }
}
```

### 2. Transaction Tools
```json
{
  "model_tx_begin": {
    "description": "Start a transaction for atomic operations",
    "input": {
      "model_id": "string"
    },
    "output": {
      "ok": true,
      "tx_id": "uuid"
    }
  },
  
  "model_tx_apply": {
    "description": "Apply ANY operations within transaction",
    "input": {
      "tx_id": "string",
      "operations": [
        {
          "type": "add_equipment|add_piping|add_valve|connect|area_deploy|...",
          "params": {}
        }
      ]
    },
    "output": {
      "ok": true,
      "results": [],
      "diff": {
        "added": {"equipment": 5, "piping": 10},
        "modified": {},
        "removed": {}
      }
    }
  },
  
  "model_tx_commit": {
    "description": "Commit or rollback transaction",
    "input": {
      "tx_id": "string",
      "action": "commit|rollback"
    },
    "output": {
      "ok": true,
      "operations_applied": 15
    }
  }
}
```

### 3. High-Level Construction Tools
```json
{
  "area_deploy": {
    "description": "Deploy a parametric template",
    "input": {
      "template": "pump_station_N+1|ro_train_2stage|tank_farm|...",
      "params": {
        "service": "string",
        "trains": "integer",
        "redundancy": "N+1|N+2|2x50%"
      },
      "anchors": {
        "inlet": "NODE:id",
        "outlet": "NODE:id"
      }
    },
    "output": {
      "ok": true,
      "components_created": 37,
      "tags_assigned": []
    }
  },
  
  "graph_connect": {
    "description": "Smart autowiring with rules",
    "input": {
      "strategy": "by_port_type|by_service|by_tag_pattern",
      "rules": {
        "from_selector": "string|pattern",
        "to_selector": "string|pattern",
        "insert_components": ["check_valve", "isolation_valve"],
        "line_class": "string"
      }
    },
    "output": {
      "ok": true,
      "connections_made": 12,
      "components_inserted": 24
    }
  },
  
  "graph_modify": {
    "description": "Structural modifications",
    "input": {
      "operation": "insert_inline|split_node|merge_nodes|remove",
      "target": "edge_id|node_id|selector",
      "components": ["valve", "instrument"],
      "position": 0.5
    },
    "output": {
      "ok": true,
      "modifications": []
    }
  }
}
```

### 4. Intelligence Tools
```json
{
  "rules_apply": {
    "description": "Apply validation rules with autofix",
    "input": {
      "model_id": "string",
      "rule_sets": ["pump_minimums", "tank_safety", "custom_rule_id"],
      "autofix": true,
      "scope": "model|area|selection"
    },
    "output": {
      "ok": false,
      "violations": [
        {
          "rule": "pump_minimums",
          "severity": "error",
          "message": "Missing suction strainer",
          "location": "P-101A",
          "can_autofix": true
        }
      ],
      "fixes_applied": 5
    }
  },
  
  "schema_query": {
    "description": "Universal schema introspection",
    "input": {
      "query_type": "list_classes|describe_class|get_attributes|get_hierarchy",
      "schema": "dexpi|sfiles",
      "class_name": "string (for describe/attributes)",
      "category": "equipment|piping|instrumentation"
    },
    "output": {
      "ok": true,
      "data": {} 
    }
  },
  
  "search_execute": {
    "description": "Universal search interface",
    "input": {
      "search_type": "by_tag|by_type|by_attributes|connected_to|pattern",
      "criteria": {
        "tag_pattern": "P-*",
        "type": "pump",
        "attributes": {"service": "feed"},
        "connected_to": "TK-101"
      },
      "model_id": "string (optional)"
    },
    "output": {
      "ok": true,
      "results": [],
      "count": 5
    }
  }
}
```

## Appendix B: Example Workflows

### Creating a Pump Station (Before: 50+ calls, After: 3 calls)

**Before (Current System):**
```javascript
// 50+ individual calls
dexpi_add_equipment({type: "Tank", tag: "TK-101"})
dexpi_add_equipment({type: "Pump", tag: "P-101A"})
dexpi_add_equipment({type: "Pump", tag: "P-101B"})
dexpi_add_equipment({type: "Pump", tag: "P-101C"})
dexpi_add_valve({type: "Strainer", tag: "S-101A"})
// ... 45 more calls for valves, piping, instruments
```

**After (New System):**
```javascript
// Call 1: Start transaction
tx_id = model_tx_begin({model_id: "plant_001"})

// Call 2: Instantiate template
model_tx_apply({
  tx_id: tx_id,
  operations: [{
    op: "area_instantiate",
    params: {
      template: "pump_station_N+1",
      params: {
        service: "Permeate Transfer",
        trains: 3,
        redundancy: "N+1",
        control: "pressure_PID"
      },
      anchors: {
        suction_header: "TK-101:Outlet",
        discharge_header: "HDR-201"
      }
    }
  }]
})

// Call 3: Commit
model_tx_commit({tx_id: tx_id})
```

## Appendix C: Staged Migration Strategy

### Compatibility Testing (Week 2-3)
1. **Functional Coverage Testing**
   - Verify all 47 old tool functionalities are available through the 12 new tools
   - Create test matrix mapping old operations to new operations
   - Run comprehensive test suite

2. **Performance Testing**
   - Benchmark old approach (50+ calls) vs new (3 calls)
   - Verify transaction rollback performance
   - Test template instantiation with large patterns

3. **Integration Testing**
   - Test with actual LLM interactions
   - Verify all response formats are consistent
   - Ensure error handling is comprehensive

### Migration Execution (Week 3, Day 5 - IF tests pass)
1. **Code Cleanup**
   - Delete all 47 old tool implementations from `src/tools/`
   - Remove old tool registrations from `server.py`
   - Delete obsolete utility functions
   - Remove old test files

2. **Server Configuration**
   - Update `server.py` to only register 12 new tools
   - Update MCP manifest (`.mcp.json`)
   - Clean up imports and dependencies

3. **Documentation Update**
   - Replace README tool list with 12 new tools
   - Archive old documentation
   - Create migration guide (for reference only)

### Post Cut-Over Validation
- Run full test suite with only 12 tools
- Verify MCP server starts correctly
- Test all example workflows
- Confirm no references to old tools remain

## Conclusion

This **revised plan** addresses both immediate needs and long-term goals:

**Immediate (Days 1-3):**
- Fix all breaking issues
- Add transaction layer maintaining compatibility
- Enable validation loop with minimal rules_apply
- Basic autowiring to prevent dangling ports
- Resource notifications for UI refresh

**Long-term (Weeks 1-3):**
- Full 12-tool implementation
- Staged migration with compatibility window
- Comprehensive testing before deprecation
- 75% reduction in tool calls
- 90% reduction in generation errors

**Key Insight:** By implementing a thin transaction layer first and keeping all 47 tools working behind it, we deliver immediate value while building toward the cleaner 12-tool architecture. The staged approach reduces risk while maintaining momentum.

Total implementation time: 3 weeks (with value delivered in 3 days)
Expected ROI: Immediate 50% improvement, eventual 75% reduction in generation time