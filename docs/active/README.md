# Active Planning Documents

This directory contains **active planning documents** that require regular updates and tracking.

## Current Active Plans

- **CORE_LAYER_MIGRATION_PLAN.md** - Multi-phase plan to migrate from pyDEXPI to core layer
  - Status: Phase 0 (not started)
  - Blockers: Symbol normalization, converter utility implementation
  - Priority: HIGH - Blocks visualization work

- **VISUALIZATION_PLAN.md** - Federated rendering platform implementation
  - Status: BLOCKED - Waiting on core layer bug fixes
  - Dependencies: CORE_LAYER_MIGRATION_PLAN Phase 0
  - Priority: HIGH - Critical for user experience

## Document Lifecycle

1. **Active** (this directory) - Plans currently being executed, require weekly updates
2. **Completed** (`docs/completed/`) - Finished initiatives archived for reference
3. **ROADMAP.md** (root) - Master project roadmap that cross-references active plans

## Updating Active Plans

When updating an active plan:
- Update status headers with current phase/progress
- Mark completed tasks with ✅
- Update blocker sections if dependencies are resolved
- Cross-reference with ROADMAP.md to keep them in sync

When a plan is completed:
- Update status header to COMPLETE
- Add completion date and final metrics
- Move to `docs/completed/`
- Update ROADMAP.md to reflect completion
