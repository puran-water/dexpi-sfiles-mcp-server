# Tool Consolidation Matrix

## Tools That Can Be Deprecated (32 tools)

### Replaced by `model_batch_apply` (28 tools)

#### DEXPI Creation Tools (14):
- [ ] dexpi_add_equipment → batch_apply({tool: "dexpi_add_equipment"})
- [ ] dexpi_add_piping → batch_apply({tool: "dexpi_add_piping"}) 
- [ ] dexpi_add_valve → batch_apply({tool: "dexpi_add_valve"})
- [ ] dexpi_add_instrumentation → batch_apply({tool: "dexpi_add_instrumentation"})
- [ ] dexpi_add_control_loop → batch_apply({tool: "dexpi_add_control_loop"})
- [ ] dexpi_connect_components → batch_apply({tool: "dexpi_connect_components"})
- [ ] dexpi_insert_valve_in_segment → batch_apply({tool: "dexpi_insert_valve_in_segment"})
- [ ] Additional DEXPI add/modify tools (7 more)

#### SFILES Creation Tools (12):
- [ ] sfiles_add_unit → batch_apply({tool: "sfiles_add_unit"})
- [ ] sfiles_add_stream → batch_apply({tool: "sfiles_add_stream"})
- [ ] sfiles_add_control → batch_apply({tool: "sfiles_add_control"})
- [ ] Additional SFILES add/modify tools (9 more)

#### Connection Tools (2):
- [ ] dexpi_connect_components → graph_connect or batch_apply
- [ ] dexpi_insert_valve_in_segment → graph_connect with inline insertion

### Replaced by `rules_apply` (2 tools)
- [ ] validate_model → rules_apply (wraps this)
- [ ] validate_round_trip → rules_apply with round_trip rule set

### Replaced by `graph_connect` (2 tools)
- [ ] dexpi_connect_components → graph_connect (smarter)
- [ ] dexpi_insert_valve_in_segment → graph_connect with inline option

## Tools to Keep (18 tools)

### Core Model Management (7):
- ✓ dexpi_create_pid
- ✓ sfiles_create_flowsheet  
- ✓ project_init
- ✓ project_save
- ✓ project_load
- ✓ project_list
- ✓ dexpi_validate_model (keep for now)

### Import/Export (6):
- ✓ dexpi_import_json
- ✓ dexpi_export_json
- ✓ dexpi_export_graphml
- ✓ sfiles_to_string
- ✓ sfiles_from_string
- ✓ sfiles_export_graphml

### Converters (2):
- ✓ dexpi_convert_from_sfiles
- ✓ sfiles_convert_from_dexpi

### New Batch Tools (3):
- ✓ model_batch_apply
- ✓ rules_apply
- ✓ graph_connect

## Testing Protocol

### Phase 1: Verify Equivalence
1. Create simple model with old tools (10 operations)
2. Create same model with batch_apply (1 operation)
3. Compare outputs - must be identical

### Phase 2: Performance Test
1. Time 50 individual add operations
2. Time 1 batch_apply with 50 operations
3. Expect >90% reduction in time

### Phase 3: Validation Test
1. Run validate_model on test model
2. Run rules_apply on same model
3. Verify identical issues found

## Migration Steps

### Day 3: Test & Mark Deprecated
1. Run all tests above
2. Add `deprecated: true` to tool schemas
3. Add deprecation warning to responses

### Day 4: Remove Deprecated Tools (Optional)
1. Remove from get_tools() methods
2. Remove handler code
3. Update README (50 → 18 tools)

## Expected Result
- **Before:** 50 tools (47 original + 3 new)
- **After:** 18 tools (15 kept + 3 new)
- **Reduction:** 64% fewer tools
- **API calls:** 95% reduction for complex operations