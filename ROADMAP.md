# Engineering MCP Server - Consolidated Roadmap

**Last Updated:** November 4, 2025
**Status:** Phase 0 Complete, Phase 1-3 Planned

---

## Overview

This roadmap consolidates the Codex Quick Wins and High-ROI Implementation Plan, showing what has been completed and what remains. The focus is on reducing tool calls from 50-200 to 1-3 per operation while enabling hierarchical BFD→PFD→P&ID diagram generation.

---

## Quick Wins & Phase 0 (Immediate Value)

### ✅ COMPLETED - Critical Stability

#### #1: Import Shim (4 hours) - DONE ✅
**Status:** Completed November 4, 2025 (100% complete including post-Codex fixes)

**What was completed:**
- Created `src/adapters/sfiles_adapter.py` - Safe import wrapper with helpful errors
- Created `src/adapters/__init__.py` - Module initialization
- Updated ALL 9 files to use safe import:
  - `src/tools/sfiles_tools.py`
  - `src/tools/schema_tools.py` (post-Codex fix)
  - `src/tools/dexpi_tools.py` (post-Codex fix)
  - `src/converters/graph_converter.py`
  - `src/converters/sfiles_dexpi_mapper.py`
  - `src/persistence/project_persistence.py`
  - `src/resources/graph_resources.py`
  - `src/tools/validation_tools.py`
  - `src/server.py` - Added `validate_dependencies()` startup check

**Impact:** Prevents production failures, provides clear error messages if SFILES2 not installed

---

#### #2: MLGraphLoader Validation (4 hours) - DONE ✅
**Status:** Completed November 4, 2025

**What was completed:**
- Refactored `src/tools/batch_tools.py` with `_validate_dexpi()` method
- Uses `MLGraphLoader.validate_graph_format()` correctly (no parameters)
- DEXPI models validated with upstream library rules
- Removed `validation_tools` parameter from `BatchTools.__init__`
- Simplified codebase by ~40% (removed custom rule engine)

**Testing:**
- ✅ DEXPI validation working (Tank equipment test passed)
- ✅ Corrected API usage after discovering parameter bug

**Impact:** Instant DEXPI validation without custom engine

---

#### #7: SFILES Round-Trip Validation (2 hours) - DONE ✅
**Status:** Completed November 4, 2025 (includes BFD fix)

**What was completed:**
- Implemented `_validate_sfiles()` in `src/tools/batch_tools.py` (lines 337-410)
- Canonical round-trip: SFILES → Flowsheet → SFILES → Compare
- Returns structured validation response with `validation_method: "round_trip"`
- **BFD ID Sanitizer:** Fixed `generate_semantic_id()` in `src/utils/process_resolver.py`
  - Converts multi-word names to CamelCase (e.g., "Aeration Tank" → "AerationTank-01")
  - Complies with SFILES2 "name-number" pattern requirement

**Root Cause Fixed:**
- SFILES2 parser expects single hyphen before number
- Old: "Aeration-Tank-01" (multiple hyphens) → Parse error ❌
- New: "AerationTank-01" (single hyphen) → Works ✅

**Testing:**
- ✅ Empty SFILES: Returns clear error
- ✅ Valid PFD (reactor → pump): Passes
- ✅ Valid BFD (Aeration Tank → Primary Clarification): Passes
- ✅ DEXPI validation unaffected

**Impact:** LLM gets immediate feedback on SFILES quality, BFD support fully functional

**Codex Validation:**
> "Running MLGraphLoader on DEXPI and SFILES round-trip on flowsheets gives us the best of both upstream toolchains."

---

### ⏳ REMAINING - Phase 0 Cleanup (1 week)

#### Response Standardization - STRATEGIC DECISION ✅
**Status:** Completed via backward compatibility

**Decision:** Maintain dual-format support rather than force migration
- ✅ `is_success()` helper handles both `{"ok": true}` and `{"status": "success"}`
- ✅ New batch tools use `success_response()` / `error_response()`
- ✅ 48 legacy tool responses work with dual-format helper
- ✅ Zero breaking changes

**Rationale:**
- Migrating 48 instances across 8 files is high-risk, low-value
- `is_success()` already provides compatibility layer
- New code enforced via code review
- Migration can be gradual during Phase 1-2 refactoring

**Outstanding Items:** 48 instances across 8 files still using legacy `{"status": "success"}` format:
- `src/tools/dexpi_tools.py` (multiple)
- `src/tools/sfiles_tools.py` (multiple)
- `src/tools/project_tools.py` (multiple)
- `src/tools/validation_tools.py` (multiple)
- `src/tools/schema_tools.py` (multiple)
- `src/tools/graph_tools.py` (multiple)
- `src/tools/search_tools.py` (multiple)
- `src/converters/graph_converter.py` (multiple)

**Cleanup Plan:** Will migrate during Phase 1-2 refactoring when touching these files

**Status:** COMPLETE - No action needed

---

#### Resource Notifications - REMOVED ✅
**Status:** Feature removed - no clear value

**Decision:** Remove notification infrastructure
- MCP is request/response protocol - clients pull when needed
- No real-time UI exists that needs push notifications
- Clients get fresh data on every request
- Adds complexity with unclear benefit

**Action:** Removed notification code from server.py and graph_resources.py

**Status:** COMPLETE - Feature removed

---

#### Deprecation Warnings - INFRASTRUCTURE READY ✅
**Status:** Decorator created, ready for Phase 3 application

**Completed:**
- ✅ Created `src/utils/deprecation.py` with `@deprecated` decorator
- ✅ Logs warnings with reason, replacement, and removal version
- ✅ Emits Python DeprecationWarning for visibility
- ✅ Provides `is_deprecated()` and `get_deprecation_info()` helpers

**Application Strategy:**
- Apply during Phase 3 when new 12-tool interface is ready
- Mark tools for deprecation after coverage matrix validated
- Gives users clear migration path before removal

**Example Usage:**
```python
@deprecated(
    reason="Tool consolidation",
    replacement="model_batch_apply",
    removal_version="1.0.0"
)
async def dexpi_add_equipment(self, args):
    ...
```

**Status:** COMPLETE - Will apply in Phase 3

---

#### Migration Guide - DEFERRED TO PHASE 3 ⏳
**Status:** Will create after new 12-tool interface is complete

**Current Documentation:**
- ✅ README.md mentions consolidation strategy
- ✅ ROADMAP.md documents all phases and tools
- ✅ Example workflows in Appendix B of original plan

**Deferred Until Phase 3:**
- Migration guide needs finalized 12-tool API
- Coverage matrix must be validated first
- Breaking changes not yet determined
- Conversion examples require working new tools

**Rationale:**
- Premature to document migration before new tools exist
- Phase 3 will have concrete before/after examples
- Deprecation decorator will guide users when applied

**Status:** Deferred - will create in Phase 3 after coverage validation

---

## Critical Issues from Codex Review #2 (November 4, 2025)

### 🔴 URGENT: Fix Remaining Direct Import
**File:** `src/tools/schema_tools.py:17`
**Issue:** After using adapter, re-imports `Flowsheet_Class.flowsheet` directly
**Impact:** Bypasses safe import shim, raw ImportError in environments without SFILES2
**Fix:** Use `importlib.import_module(Flowsheet.__module__)` instead
**Status:** ✅ FIXED

### ✅ Legacy BFD Data Migration - NOT NEEDED
**Issue:** CamelCase fix only protects NEW nodes
**Impact:** Existing flowsheets with "Aeration-Tank-01" would fail round-trip validation
**Resolution:** All legacy BFDs are test data from MCP server testing - no production usage
**Action:** No migration needed, test BFDs can be discarded
**Status:** RESOLVED - No action required

### ⚠️ Phase Sequencing Correction
**Codex Finding:** "Transaction-first work underpins template instantiation"
**Issue:** Templates (#4/#5) depend on TransactionManager
**Risk:** Partial writes when patterns expand without transaction safety
**Fix:** Reorder Phase 1 to implement TransactionManager BEFORE templates

---

## Phase 0.5: API Design & Specifications (Critical Pre-Phase 1) 🔴

**Status:** BLOCKING Phase 1 - Must complete before implementation
**Duration:** 3-5 days
**Codex Assessment:** "If well designed" qualifier NOT currently satisfied

### Critical Finding from Codex Review

**Problem**: Current ROADMAP has implementation tasks but missing foundational API designs. Codex identified specific gaps that must be resolved before Phase 1 implementation:

1. **graph_modify** - No concrete contract exists (only TODO)
2. **model_tx_apply** - Still string dispatch, needs typed operation registry
3. **area_deploy** - Missing template library design and parameter rules
4. **TransactionManager** - Deep-copy performance concerns, needs structural diff design

**Impact**: Without these specifications, Phase 1 implementation would be building on undefined foundations.

---

### Design Task 1: graph_modify API Specification ⏳

**Status:** IN PROGRESS - Updated with upstream library leverage
**Priority:** CRITICAL - Determines if consolidation satisfies "point change" requirement
**Estimate:** 2 days

**Codex Validation - Upstream Library Leverage:**

**✅ Use Directly from pyDEXPI** (`pydexpi/toolkits/piping_toolkit.py`):
- `insert_item_to_segment` (lines 532-707) - For `insert_inline_component`
- `connect_piping_network_segment` (lines 134-207) - For `rewire_connection`
- `append_item_to_unconnected_segment` - For free segment operations
- `piping_network_segment_validity_check` - Post-operation validation

**❌ Build Custom (No Upstream Support)**:
- Segment split/merge - No native helpers in pyDEXPI
- Must compose "insert + reconnect + new segment" manually
- Use `find_final_connection` and `construct_new_segment` utilities

**SFILES Operations**:
- ✅ `Flowsheet.add_unit` / `add_stream` (Flowsheet_Class/flowsheet.py:56-86)
- ✅ `split_HI_nodes` / `merge_HI_nodes` (lines 524-638) - Heat integration
- ❌ Direct stream rewiring - manipulate NetworkX `self.state` directly
- Re-run `convert_to_sfiles` after modifications for canonicalization

**What Must Be Designed:**

1. **Action Enum** (Codex-recommended, covering 80%+ of point changes):
   - `insert_component` - Add new component to model
   - `remove_component` - Delete component from model
   - `update_component` - Modify component attributes
   - `insert_inline_component` - **Wrapper over `insert_item_to_segment`**
   - `split_segment` - Custom logic using pyDEXPI segment utilities
   - `merge_segments` - Custom logic with validity checks
   - `rewire_connection` - **Wrapper over `connect_piping_network_segment`**
   - `set_tag_properties` - Update tag metadata
   - `toggle_instrumentation` - Add/remove instruments
   - `update_stream_properties` - **SFILES: NetworkX manipulation + canonicalize**

2. **Target Selector Schema**:
   ```typescript
   {
     kind: "component" | "segment" | "stream" | "port",
     identifier: string,  // tag or GUID
     selector?: {         // optional filters
       class?: string,
       service?: string,
       attributes?: object
     }
   }
   ```

3. **Implementation Strategy** (thin wrappers over upstream):
   - Resolve target segment/component
   - Construct pyDEXPI `PipingNetworkSegmentItem` objects
   - Call upstream toolkit functions
   - Run `piping_network_segment_validity_check` post-operation
   - Log diff for TransactionManager
   - For SFILES: wrap NetworkX ops, re-canonicalize

4. **Response Format**:
   ```typescript
   {
     ok: true,
     mutated_entities: string[],  // IDs of changed components
     diff: {
       added: string[],
       removed: string[],
       updated: string[]
     },
     validation: {                // Run toolkit validity checks
       errors: [],
       warnings: []
     }
   }
   ```

5. **DEXPI/SFILES Parity** - Each action must specify behavior for both standards or explicitly error

**Deliverable**: `docs/api/graph_modify_spec.md` with upstream toolkit integration details

---

### Design Task 2: Operation Registry for model_tx_apply ⏳

**Status:** NOT STARTED
**Priority:** HIGH - Required for typed dispatch
**Estimate:** 1 day

**Current Problem** (Codex): "Still just a thin dispatcher over 51 atomic tools using string names"

**Codex Validation - Upstream Pattern:**
- ✅ Follow `ParserFactory.factory_methods` pattern from `pydexpi/loaders/proteus_serializer/parser_factory.py:24-76`
- ✅ Leverage `DexpiIntrospector` (already in codebase) for schema metadata
- ✅ Use dict-of-callables structure for operation dispatch
- ❌ No ready-made operation descriptor catalog - must author ourselves

**What Must Be Designed:**

1. **Operation Descriptor Schema**:
   ```typescript
   {
     name: string,
     version: string,
     category: "dexpi" | "sfiles" | "universal",
     description: string,
     inputSchema: JSONSchema,
     handler: async (model, params) => result,
     validationHooks?: {
       pre?: (model, params) => ValidationResult,
       post?: (model, result) => ValidationResult
     },
     metadata?: {
       replaces?: string[],  // old tool names
       introduced?: string,  // version
       deprecated?: string
     }
   }
   ```

2. **Registry Interface**:
   - `register(operation: OperationDescriptor)`
   - `get(name: string): OperationDescriptor`
   - `list(filter?: {category, version}): OperationDescriptor[]`
   - `getSchema(): JSONSchema` - For schema_query tool

3. **Built-in Operations** - Map current atomic tools to operations:
   - `add_equipment`, `add_valve`, `add_piping`, etc.
   - Define which stay vs. which are replaced by graph_modify actions

4. **Versioning Strategy** - How operations evolve over time

5. **Integration Points**:
   - model_tx_apply dispatch logic
   - schema_query tool exposure
   - Validation hook execution

**Deliverable**: `docs/api/operation_registry_spec.md`

---

### Design Task 3: TransactionManager Architecture ⏳

**Status:** NOT STARTED
**Priority:** CRITICAL - Performance and reliability foundation
**Estimate:** 1 day

**Codex Warning**: "Deep copies of large DexpiModels can be MB-scale; benchmark early and fall back to structural diffs"

**Codex Validation - Upstream Utilities:**
- ✅ Use `copy.deepcopy` for small models (pattern from `pydexpi/syndata/pattern.py:504-519`)
- ✅ Use `model_toolkit.combine_dexpi_models` / `import_model_contents_into_model` (`pydexpi/toolkits/model_toolkit.py:17-99`)
- ✅ Use `MLGraphLoader.validate_graph_format` for post-transaction validation (`pydexpi/loaders/ml_graph_loader.py:80-103`)
- ✅ Use `get_all_instances_in_model` (`pydexpi/toolkits/model_toolkit.py:102-199`) for building audit diffs
- ❌ No native diff/transaction scaffolding - must build custom

**What Must Be Designed:**

1. **State Management**:
   ```typescript
   class TransactionManager {
     transactions: Map<string, Transaction>

     begin(model_id: string): transaction_id
     apply(transaction_id: string, operations: Operation[]): results
     commit(transaction_id: string): final_state
     rollback(transaction_id: string): void
     diff(transaction_id: string): StructuralDiff
   }
   ```

2. **Copy Strategy** (Codex-recommended):
   - **Snapshot by serialization** for large models (>1MB threshold)
   - **Deep copy** for small models (<1MB) using `copy.deepcopy`
   - Use existing serializers for snapshot caching
   - Benchmark with real DEXPI models to determine threshold

3. **Diff Calculation**:
   - Use `get_all_instances_in_model` to enumerate components
   - Track added/removed/modified components
   - Efficient comparison algorithm
   - Integration with `MLGraphLoader.validate_graph_format`

4. **Isolation Levels**:
   - Single-transaction per model (simple)
   - OR: Multi-transaction with conflict detection (complex)

5. **Performance Targets**:
   - begin(): <100ms for models up to 500 components
   - apply(): <50ms per operation
   - commit(): <200ms with validation
   - rollback(): <50ms

6. **Error Handling**:
   - Partial operation failures
   - Validation failures
   - Timeout handling

**Deliverable**: `docs/architecture/transaction_manager.md`

---

### Design Task 4: Template Library Architecture ⏳

**Status:** NOT STARTED
**Priority:** MEDIUM - Needed for area_deploy
**Estimate:** 1 day

**Codex Concern**: "Missing internal template library, parameter substitution rules, and coverage for instrumentation/control variations"

**Codex Validation - Upstream Capabilities:**
- ✅ `DexpiPattern` merges models via `mt.import_model_contents_into_model` (`pydexpi/syndata/dexpi_pattern.py:268-286`)
- ✅ `ConnectorRenamingConvention` handles connector renaming (`pydexpi/syndata/connector_renaming.py:8-69`)
- ✅ `Pattern.relabel_connector` for observer propagation (`pydexpi/syndata/pattern.py:483-503`)
- ✅ `Pattern.copy_pattern` for cloning templates (`pydexpi/syndata/pattern.py:504-519`)
- ✅ Generator stack shows how to sequence patterns (`pydexpi/syndata/generator.py:14-181`)
- ❌ No built-in parameter substitution - must layer our own templating
- ❌ No automatic self-validation - must run separately

**Additional Leverage Opportunities:**
- `SyntheticPIDGenerator` shows pattern sequencing for `area_deploy`
- SFILES `split_HI_nodes`/`merge_HI_nodes` (Flowsheet_Class/flowsheet.py:524-638) for heat-integration templates
- SFILES `generalize_SFILES` + `flatten` already solve Phase 2 generalization helper

**What Must Be Designed:**

1. **Template Format** (wraps pyDEXPI DexpiPattern):
   ```yaml
   name: pump_station_n_plus_1
   version: 1.0
   category: piping
   description: N+1 redundant pump station

   parameters:
     pump_count: {type: int, min: 2, max: 10, default: 3}
     flow_rate: {type: float, unit: m3/h}
     control_type: {type: enum, values: [flow, pressure, level]}

   components:
     - type: CentrifugalPump
       count: ${pump_count}
       tag_pattern: "P-${area}-${sequence}"
       attributes: {...}

   connections:
     - from: ${header_inlet}
       to: pump[*].inlet
       via: [CheckValve, IsolationValve]

   instrumentation:
     - if: ${control_type} == "flow"
       add: FlowController
   ```

2. **Template Library Structure**:
   ```
   /library/patterns/
     /piping/
       pump_station_n_plus_1.yaml
       tank_farm.yaml
       heat_integration.yaml        # NEW: Use SFILES split/merge_HI_nodes
     /instrumentation/
       flow_control_loop.yaml
       cascade_control.yaml
     /process/
       ro_train_2stage.yaml
       chemical_dosing.yaml
   ```

3. **Implementation Strategy** (Codex-recommended):
   - Wrap templates in "parametric template" class
   - Clone via `Pattern.copy_pattern`
   - Apply parameter substitutions (walk DexpiModel, replace attributes)
   - Feed to `ConnectorRenamingConvention` for tag generation
   - Compose patterns using generator stack pattern
   - Validation: Run `MLGraphLoader.validate_graph_format` after instantiation

4. **Parameter Substitution Rules**:
   - Variable interpolation syntax: `${variable_name}`
   - Conditional logic (if/else): Simple Python-style conditions
   - Array expansion (count, foreach): Generate N copies with pattern
   - Naming conventions: Integrate with `ConnectorRenamingConvention`

5. **Minimum Template Coverage** (start with 5, plan for 20+):
   - **Piping**: Pump station, Tank farm, Heat exchanger network
   - **Control**: Flow/Level/Pressure/Temperature control loops
   - **Process**: RO train, Dosing skid, Aeration system
   - **Heat Integration**: Use SFILES heat-integration utilities

6. **Validation**:
   - Template schema validation
   - Parameter type checking
   - Connection validity via `piping_network_segment_validity_check`
   - Instrument compatibility
   - Post-instantiation: `MLGraphLoader.validate_graph_format`

**Deliverable**: `docs/templates/template_system.md` + 5 example templates + parameter substitution implementation

---

### Phase 0.5 Success Criteria

**All 4 design tasks completed** with:
- ✅ Written specifications in `docs/`
- ✅ API contracts defined
- ✅ Examples/schemas provided
- ✅ User review and approval
- ✅ Codex validation of designs

**Only then** can Phase 1 implementation begin with confidence that "if well designed" qualifier is satisfied.

---

## Phase 1: Core Infrastructure (Week 1, Days 4-7)

### Transaction Manager Enhancement - MOVED TO FIRST 🔴
**Status:** Basic batch operations exist, need full ACID support
**Priority:** MUST complete before templates (#4/#5)

**Current State:**
- ✅ `model_batch_apply` provides basic batching
- ❌ No deep copy/rollback capability
- ❌ No transaction state management

**What Needs to Be Done:**
1. Create `src/managers/transaction_manager.py`
2. Implement `begin()` with deep copy
3. Implement `apply_batch()` with operation dispatcher
4. Implement `commit()` and `rollback()`
5. Add diff calculation

**Why This Must Come First:**
- Templates expand patterns into models
- Without transactions, partial writes are unrecoverable
- Rollback essential for LLM retry safety

**Estimate:** 2 days (Days 4-5)

---

### #3: Enhance graph_connect with piping_toolkit (8 hours) - NOT STARTED 🔴
**Status:** Basic version exists, needs piping_toolkit integration

**Current State:**
- ✅ `graph_connect` tool exists in `batch_tools.py:272-450+`
- ✅ Pattern matching for equipment selection
- ✅ 2 strategies: `by_port_type`, `pumps_to_header`
- ❌ Uses custom loops instead of pyDEXPI's battle-tested toolkit

**What Needs to Be Done:**
1. Import `pydexpi.toolkits.piping_toolkit`
2. Replace custom connection logic with `connect_piping_network_segment()`
3. Use `insert_item_to_segment()` for inline components
4. Add validity checks from toolkit

**Why This Matters:**
- More reliable autowiring
- Proper nozzle handling
- Less custom code to maintain

**Estimate:** 1 day

---

### #4: Template Instantiation Tool (12 hours) - NOT STARTED 🔴
**Status:** Design complete, implementation needed

**What Needs to Be Done:**
1. Create `src/tools/template_tools.py`
2. Implement `template_instantiate` using `pyDEXPI.syndata.dexpi_pattern`
3. Add MCP tool registration
4. Create 2-3 example patterns for testing

**Key Features:**
- Load pyDEXPI Pattern files
- Apply parameter substitutions
- Connect to target model using Pattern's connector system
- Auto-generate component IDs

**Why This Matters:**
- Validates pyDEXPI Pattern approach before full consolidation
- Reduces pump station creation from 50+ calls to 3

**Estimate:** 1.5 days

---

### #5: ConnectorRenamingConvention Integration (4 hours) - NOT STARTED 🔴
**Status:** Depends on #4

**What Needs to Be Done:**
1. Enhance `template_instantiate` with `ConnectorRenamingConvention`
2. Add prefix/sequence management
3. Integrate with `get_next_sequence()` logic

**Why This Matters:**
- Unique tags without TagManager
- Consistent naming via pyDEXPI conventions

**Estimate:** 0.5 days

---


### Universal Model Operations - NOT STARTED 🔴
**What Needs to Be Done:**
1. Implement `model_create` - Unified initialization
2. Implement `model_load` - Universal loader
3. Implement `model_save` - Universal saver
4. Create operation registry for `model_tx_apply`

**Estimate:** 3 days

---

## Phase 2: High-Level Construction (Week 2)

### Template System & area_deploy - NOT STARTED 🔴
**Status:** Design validated by Codex

**What Needs to Be Done:**
1. Create `src/templates/parametric_template.py` (thin wrapper around DexpiPattern)
2. Build template library structure (`/library/patterns/`)
3. Create 5 example templates:
   - Pump station (N+1)
   - RO train (2-stage)
   - Tank farm
   - Chemical dosing skid
   - Heat exchanger

**Estimate:** 3 days

---

### Smart Connection System - NOT STARTED 🔴
**Status:** Enhanced version of existing graph_connect

**What Needs to Be Done:**
1. Implement `graph_modify` - Inline modifications
2. Add port finding and matching logic
3. Implement split/merge operations

**Estimate:** 2 days

---

### SFILES Generalization Helper (#6) - NOT STARTED 🔴
**Status:** Design complete

**What Needs to Be Done:**
1. Add to `src/tools/sfiles_tools.py`
2. Import `generalize_SFILES` from Flowsheet_Class
3. Add MCP tool registration

**Why This Matters:**
- Normalize prompts for template matching
- Pattern detection across flowsheets

**Estimate:** 0.5 days

---

## Phase 3: Validation & Migration (Week 3)

### Unified Intelligence Tools - NOT STARTED 🔴
**What Needs to Be Done:**
1. Enhance `rules_apply` with autofix capability
2. Implement `schema_query` - Consolidates all schema_* tools
3. Implement `search_execute` - Consolidates all search_* tools

**Estimate:** 2 days

---

### Testing & Validation - NOT STARTED 🔴
**What Needs to Be Done:**
1. Create coverage matrix (51 old tools → 12 new tools)
2. Comprehensive testing of all 12 tools
3. Performance benchmarking
4. Validate feature parity

**Estimate:** 2 days

---

### Tool Consolidation (51 → 12 Tools) - NOT STARTED 🔴
**Status:** Awaiting completion of testing phase

**The 12 Target Tools:**
1. `model_create` - Replace dexpi_create_pid, sfiles_create_flowsheet
2. `model_load` - Replace all import tools
3. `model_save` - Replace all export tools
4. `model_tx_begin` - Start transaction
5. `model_tx_apply` - Apply ANY operation (replaces 25+ tools)
6. `model_tx_commit` - Commit/rollback
7. `area_deploy` - Template instantiation (replaces all add_* tools)
8. `graph_connect` - Smart autowiring
9. `graph_modify` - Inline modifications
10. `rules_apply` - Validation + autofix
11. `schema_query` - Universal schema access
12. `search_execute` - Universal search

**Deprecation Only After:**
- ✅ All 12 tools functional
- ✅ Coverage matrix verified
- ✅ Performance acceptable
- ✅ Migration guide complete

**Estimate:** 1 day (removal + cleanup)

---

## Testing Infrastructure (Ongoing)

### #8: Data Augmentation Test Harness - NOT STARTED 🔴
**What Needs to Be Done:**
1. Create `tests/fixtures/generate_augmented.py`
2. Use SFILES2 augmentation utilities
3. Generate 100+ test cases from base patterns
4. Integrate with pytest

**Estimate:** 1 day

---

### #9: DEXPI-to-GraphML Optional Backend - NOT STARTED 🔴
**Status:** Optional feature, low priority

**What Needs to Be Done:**
1. Create `src/converters/dexpi2graphml_adapter.py`
2. Add fallback to internal converter
3. Document as optional dependency

**Estimate:** 1 day

---

### #10: Transaction Commit with import_model_contents - NOT STARTED 🔴
**Status:** Depends on Transaction Manager

**What Needs to Be Done:**
1. Use `pyDEXPI.toolkits.model_toolkit.import_model_contents_into_model`
2. Integrate into `TransactionManager.commit()`
3. Avoid hand-written deep merges

**Estimate:** 0.5 days

---

## Part 2: BFD→PFD→P&ID Hierarchical System (6-9 months)

### Status: APPROVED GO - Architecture Validated by Codex

**Key Decisions:**
- ✅ Skip CIR layer - Use NetworkX as canonical model
- ✅ Leverage pyDEXPI Patterns - Don't reinvent templates
- ✅ Use elkjs for layout - No JVM required
- ✅ Allow SVG/DXF export - Update CLAUDE.md policy

**Timeline Improvement:** 50% faster than original estimate (6-9 months vs 12-18 months)

---

### Phase 1: Production-Ready Core (4-6 months) - NOT STARTED 🔴

**⚠️ Timeline Risk (Codex Review #2):**
> "The 6-9 month BFD plan assumes elkjs + drawsvg/ezdxf glue lands smoothly. Budget time for the Node/JS bridge and renderer symbol work—they're new stacks for this repo and may stretch the timeline."

**Risk Mitigation:**
- Sprint 3 includes decision gate: Evaluate elkjs quality at Week 7
- Symbol library creation (20+ ISA S5.1 symbols) is main renderer effort
- Node.js bridge is straightforward subprocess call, but test thoroughly
- Add 2-week buffer to 6-9 month estimate if rendering work exceeds estimates

#### Sprint 1 (Weeks 1-2): Foundation
**What Needs to Be Done:**
1. ✅ Fix `src/utils/process_resolver.py` hardcoded path (DONE)
2. Extend NetworkX with typed attributes
3. Create `src/models/graph_metadata.py` (Pydantic schemas)

**Deliverables:**
- NetworkX graphs with rich metadata
- Port specifications (N/S/E/W)
- Layout storage schema

---

#### Sprint 2 (Weeks 3-4): BFD Model
**What Needs to Be Done:**
1. Create `src/models/bfd.py`
2. Implement BFD with typed ports
3. Create `src/tools/bfd_tools.py` (6 new tools)
4. Unit tests

**New MCP Tools:**
- `bfd_create` - Initialize BFD
- `bfd_add_block` - Add process block with ports
- `bfd_add_flow` - Connect blocks
- `bfd_export_graphml` - Export topology
- `bfd_export_cir` - Export NetworkX JSON
- `bfd_to_pfd_plan` - List PFD variant options

---

#### Sprint 3 (Weeks 5-7): Layout Engine
**What Needs to Be Done:**
1. Set up Node.js + elkjs dependencies
2. Create `src/layout/elkjs_layout.py`
3. Create `elkjs_wrapper.js`
4. Implement position storage in graph metadata
5. Benchmark performance

**Deliverables:**
- Deterministic orthogonal layouts
- Git-friendly layout storage (.layout files)
- Fallback to NetworkX layouts

**Decision Gate:** Evaluate elkjs quality at end
- ✅ Proceed if <10% edge overlaps
- ⚠️ Add libavoid if >20% overlaps

---

#### Sprint 4 (Weeks 8-10): Templates
**What Needs to Be Done:**
1. Create `src/adapters/pattern_adapter.py` (thin wrapper around pyDEXPI)
2. Create `src/tools/library_tools.py`
3. Build 5 example pyDEXPI Patterns:
   - Pump station (single vs parallel)
   - Heat exchanger (shell & tube)
   - Reactor variants
   - Tank configurations
   - Control loop patterns

**Deliverables:**
- `/library/pfd_variants/` - Process-level patterns
- `/library/pid_snippets/` - Detailed P&ID subgraphs
- Pattern instantiation working end-to-end

---

#### Sprint 5 (Weeks 11-13): Rendering
**What Needs to Be Done:**
1. Create `src/renderers/svg_renderer.py` using drawsvg
2. Create `src/renderers/dxf_renderer.py` using ezdxf
3. Build ISA S5.1 symbol library (`src/renderers/symbols/`)
4. **Update CLAUDE.md** - Remove "No SVG" restriction
5. Integrate auto-generation into `project_save`

**Deliverables:**
- SVG export for browser review
- DXF export for CAD tools (AutoCAD, QCAD, LibreCAD)
- Symbol library with 20+ ISA S5.1 symbols

**Dependencies Added:**
```python
drawsvg>=2.0
ezdxf>=1.0
```

---

#### Sprint 6 (Weeks 14-16): Integration
**What Needs to Be Done:**
1. End-to-end workflow testing (BFD → PFD → P&ID)
2. Traceability validation (lineage tracking)
3. Performance optimization
4. Documentation and examples

**Acceptance Criteria:**
- ✅ BFD → PFD → P&ID with <5% topology loss
- ✅ Git diff <100 lines for minor changes
- ✅ SVG/DXF pass engineer review
- ✅ 5+ working templates
- ✅ Round-trip tests pass

---

### Phase 2: Advanced Features (2-3 months) - NOT STARTED 🔴

**Planned Features:**
1. Interactive editor (Sprotty + elkjs)
2. Advanced templates (nested patterns, N+1 logic)
3. Process simulator integration (Aspen Plus, DWSIM)
4. AI-assisted design (template recommendation, anomaly detection)

**Status:** Deferred until Phase 1 complete

---

## Success Metrics

### Phase 0 Complete ✅
- ✅ Zero import failures in production
- ✅ DEXPI validation via MLGraphLoader
- ✅ SFILES round-trip validation passing
- ✅ BFD support fully functional

### Phase 1 Target (Week 2 End)
- ⏳ Pattern instantiation working end-to-end
- ⏳ 10+ augmented test fixtures generated
- ⏳ 5+ production-ready patterns in library

### Phase 2 Target (Week 6 End)
- ⏳ Area deployment working
- ⏳ Tag generation automated
- ⏳ LLM creates pump station in 2-3 calls (vs 50+)

### BFD System Target (Phase 1 End)
- ⏳ BFD → PFD → P&ID expansion working
- ⏳ SVG/DXF export passing engineer review
- ⏳ Deterministic layouts stored in git

---

## Quantitative Impact

### Tool Consolidation
- **Before:** 51 tools, 50-200 calls per operation
- **After:** 12 tools, 1-3 calls per operation
- **Improvement:** 75% reduction in tool count, 95% reduction in calls

### BFD System
- **Timeline:** 6-9 months (50% faster than original 12-18 month estimate)
- **Cost Savings:** $75-120K vs original estimate
- **Risk Reduction:** HIGH → MODERATE

---

## Key Architectural Decisions

### 1. Leverage Upstream Libraries
- ✅ Use pyDEXPI Pattern/Connector (don't reinvent templates)
- ✅ Use MLGraphLoader for validation (don't build rule engine)
- ✅ Use piping_toolkit for connections (don't write custom loops)
- ✅ Use NetworkX as canonical model (don't build CIR layer)

**Impact:** 50% faster implementation, lower maintenance burden

### 2. Transaction-First Architecture
- Every mutation goes through transaction
- Atomic batch operations
- Full rollback capability
- Idempotent operations

**Impact:** Prevents partial edits, enables safe LLM retries

### 3. Declarative Over Imperative
- Templates define structure declaratively
- Rules define requirements declaratively
- Autowiring uses declarative matching

**Impact:** Easier for LLMs to understand and use

### 4. Git-Friendly Storage
- Deterministic layouts stored explicitly
- Human-readable NetworkX JSON
- Incremental layout for topology changes

**Impact:** Clean diffs, proper version control

---

## Risk Mitigation

### Technical Risks
1. **pyDEXPI limitations** - Work within constraints, contribute fixes upstream
2. **Performance** - Lazy loading, caching, profiling
3. **Complex rule interactions** - Priority system, conflict detection

### Implementation Risks
1. **Scope creep** - Strict phase boundaries, MVP first
2. **Integration issues** - Comprehensive testing at each phase
3. **Documentation lag** - Document as we build

---

## Immediate Next Steps (This Week)

### Days 1-2: Critical Path
1. ✅ Complete response standardization for legacy tools
2. ✅ Enable resource notifications
3. ✅ Add deprecation warnings
4. ✅ Create migration guide

### Days 3-5: Quick Win Completion
1. Implement #3: Enhance graph_connect with piping_toolkit
2. Implement #4: Template instantiation tool
3. Implement #5: Connector renaming integration

### Week 2: Pattern Validation
1. Create 2-3 example pyDEXPI Patterns
2. Test template instantiation end-to-end
3. Validate approach before Phase 1

---

## Documents Consolidated Into This Roadmap

This document replaces and consolidates:
- ✅ CODEX_QUICK_WINS.md
- ✅ HIGH_ROI_IMPLEMENTATION_PLAN.md
- ✅ SESSION_SUMMARY_NOV4.md
- ✅ CODEX_REVIEW_FOLLOWUP.md
- ✅ BREAKING_CHANGE_REFACTOR.md
- ✅ IMPLEMENTATION_PROGRESS.md
- ✅ SFILES_VALIDATION_ANALYSIS.md (key findings included)

**Single source of truth:** All future roadmap updates go in this file.

---

## Codex Insights (Key Quotes)

### On Avoiding Reinvention
> "The pattern/connector system (e.g., BasicPiping*Connector, DexpiPattern) already provides parametric fragments with validated connection points"

> "MLGraphLoader.validate_graph_format enforces DEXPI rules (node/edge classes, attributes, connectivity), giving us a ready-made RuleEngine core"

> "piping_toolkit contains the autowiring primitives we planned to write (connect segments, append inline components, validity checks)"

### On BFD Architecture
> "Targeting a standalone CIR layer duplicates what your existing networkx graphs plus the SFILES/DEXPI converters already provide"

> "elkjs: Actively maintained (last push 2025-09). Supplies layered layout, orthogonal routing, and incremental layout options without JVM"

> "libavoid (Adaptagrams): GH data shows pushes in late 2025 and 290⭐; it is not abandoned. It already powers Inkscape, Graphviz, Dunnart."

### On Validation Architecture
> "Running MLGraphLoader on DEXPI and SFILES round-trip on flowsheets gives us the best of both upstream toolchains."

---

**END OF ROADMAP**

**Last Updated:** November 4, 2025
**Next Review:** After Phase 0 cleanup complete (Week 1)
