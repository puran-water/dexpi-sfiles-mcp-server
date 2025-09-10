# Engineering MCP Server — Tool Test Bug Log

Date: 2025-09-10

Scope: Results from exercising all engineering-mcp tools via MCP client in this workspace.

Environment
- Workspace: /home/hvksh/processeng
- Server entry: engineering-mcp-server/src/server.py (stdio)
- Notes: Network disabled; filesystem write to workspace allowed.

Summary of Tested Tool Families
- DEXPI: create/import/export, equipment/piping/instrumentation/control, connect, convert, validate
- SFILES: create/from/to string, add unit/stream/control, export, parse/validate, canonical form, convert
- Validation: validate_model, validate_round_trip
- Graph: analyze, find_paths, detect_patterns, calculate_metrics, compare_models
- Search: by_tag, by_type, by_attributes, connected, query_model_statistics, by_stream
- Project: init, save, list, load
- Batch: model_batch_apply, rules_apply, graph_connect

Key Bugs and Inconsistencies

DEXPI
1) dexpi_validate_model crashes on valid model
   - Repro: dexpi_create_pid → add equipment/piping → dexpi_validate_model(model_id)
   - Error: 'DexpiModel' object has no attribute 'metaData'
   - Root cause: Inconsistent attribute casing used across code (metaData vs metadata). validate_model references metaData; Project persistence uses metadata.
   - Fix: Normalize to one attribute (prefer metadata) across all uses.

2) dexpi_export_graphml returns empty graph for populated model
   - Repro: Build simple model; dexpi_export_graphml(model_id)
   - Result: Valid GraphML with zero nodes/edges
   - Likely cause: MLGraphLoader conversion failure swallowed in converter (returns empty graph on exception).
   - Fix: Surface conversion exceptions and/or validate model connectivity before export.

3) dexpi_import_json fails
   - Repro: dexpi_export_json → dexpi_import_json(json_content, model_id="X")
   - Error: JsonSerializer.load() missing 1 required positional argument: 'filename'
   - Root cause: JsonSerializer.load signature expects (directory, filename); code passes a single path.
   - Fix: Write temp file and call load(temp_dir, basename) or use serializer.model_from_dict on parsed JSON.

4) Instrumentation type enum vs code mismatch
   - Issue: inputSchema enumerates generic types (e.g., Transmitter) while _add_instrumentation special-cases FlowTransmitter/LevelTransmitter/etc.
   - Impact: Users cannot select FlowTransmitter via schema, but code expects it for enriched behavior.
   - Fix: Align enum with specialized class names or relax condition (e.g., detect by tag prefix FT/LT/PT/TT).

5) Mixed response envelopes
   - Affected: dexpi_add_instrumentation, dexpi_add_valve (and some SFILES tools) return raw dicts instead of success_response envelope.
   - Impact: Inconsistent client handling; BatchTools relies on is_success but payload shape varies.
   - Fix: Standardize all tool returns via success_response/error_response.

6) validate_model (unified) fails on original DEXPI model
   - Error: 'NoneType' object has no attribute 'controlledActuator'
   - Likely in connectivity/ISA validation due to partially populated control loop internals.
   - Fix: Harden validators for optional references or ensure loop creation populates required links.

SFILES
7) sfiles_export_graphml throws dict value error
   - Repro: create_flowsheet → add units/streams → sfiles_export_graphml
   - Error: GraphML does not support type <class 'dict'> as data values.
   - Root cause: Writes flowsheet.state directly to GraphML; bypasses GraphMLSanitizer.
   - Fix: Use converters.UnifiedGraphConverter.sfiles_to_graphml (which sanitizes).

8) sfiles_canonical_form returns error
   - Error: "Unexpected result from convert_to_sfiles"
   - Root cause: Assumes convert_to_sfiles returns tuple/str; in practice it often sets flowsheet.sfiles and returns None. Also calls SFILES_parser with an argument.
   - Fix: After create_from_sfiles, call convert_to_sfiles(...); read flowsheet.sfiles. Remove arg to SFILES_parser.

9) sfiles_add_control response + naming
   - Returns raw dict (not standardized). Also renames control_name (e.g., "FC-001" → "C-001"), losing FC prefix in the node label (though control_type is stored).
   - Fix: Wrap via success_response and consider retaining requested label or including mapping info.

Graph Tools
10) graph_calculate_metrics errors on directed graphs
    - Error: "not implemented for directed type" (local_efficiency on DiGraph)
    - Fix: Convert to undirected for local/global efficiency (graph.to_undirected()).

Search/Statistics
11) SFILES node type detection mismatched
    - search_by_type and query_model_statistics use node attribute 'type'; flowsheet nodes actually use 'unit_type'.
    - Symptoms: All nodes reported as type "Unknown"; search_by_type returns unrelated nodes.
    - Fix: Use 'unit_type' for SFILES; adjust include_subtypes logic to only check component_type in node_type.

12) search_by_type include_subtypes logic too permissive
    - Condition uses (component_type in node_type or node_type in component_type); with empty/unknown types this returns true and matches all.
    - Fix: Drop the node_type in component_type clause; ensure node_type non-empty.

Project Tools
13) project_load for DEXPI fails to reload saved JSON
    - Error: KeyError-like on ID '5bab3950-...' during load_dexpi
    - Likely pyDEXPI JSON rehydrate issue with references in instrumentation/signal links.
    - Fix: Investigate pydexpi JsonSerializer round-trip for instrumentation references; possibly sanitize before save.

Code Quality/Structural
14) Stray, invalid code block in dexpi_tools.py
    - Location: Around lines ~1386–1402 (class body) referencing args/project_path without a function context.
    - Risk: Should cause import-time NameError; may be masked by indentation or dead code.
    - Fix: Remove obsolete block.

15) GraphResourceProvider SFILES 'string' export likely incorrect
    - Uses flowsheet.convert_to_sfiles(...) as return value; API typically sets flowsheet.sfiles and returns None.
    - Fix: Call convert_to_sfiles then read flowsheet.sfiles.

Other Notes
- dexpi_export_graphml returns empty graph silently on conversion errors; consider returning validation issues alongside export to guide users.
- Some tool schemas include optional fields that aren’t used; pruning or documenting no-ops would help UX.

