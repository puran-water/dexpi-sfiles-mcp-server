/**
 * Symbol Library Module
 *
 * Provides external symbol library integration for the Proteus XML viewer.
 * This module allows using our curated symbol catalog (merged_catalog.json)
 * instead of or alongside embedded ShapeCatalogue shapes from DEXPI XML.
 */

// Re-export all public interfaces and classes
export type {
    SymbolEntry,
    PortDefinition,
    BoundingBox,
    AnchorPoint
} from './SymbolLibraryLoader';

export {
    SymbolLibraryLoader,
    getGlobalSymbolLibrary,
    initGlobalSymbolLibrary,
    clearGlobalSymbolLibrary
} from './SymbolLibraryLoader';

export type {
    SvgImportOptions,
    TransformOptions
} from './SvgToPaperJs';

export {
    svgToPaperJsGroup,
    cloneForPlacement,
    applyTransforms,
    normalizeColors,
    getLocalBounds,
    setStrokeWeight
} from './SvgToPaperJs';

export {
    ExternalSymbol
} from './ExternalSymbol';
