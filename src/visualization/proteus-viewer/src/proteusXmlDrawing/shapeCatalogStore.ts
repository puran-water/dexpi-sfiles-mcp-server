/**
 * Shape Catalog Store
 *
 * Central registry for shape lookups during Proteus XML rendering.
 * Now supports both embedded ShapeCatalogue shapes from XML AND
 * external symbols from our curated symbol library (merged_catalog.json).
 *
 * Lookup Priority (configurable):
 * 1. External symbol library (for corporate-standard consistency) - DEFAULT
 * 2. Embedded ShapeCatalogue (fallback for symbols not in library)
 *
 * Or:
 * 1. Embedded ShapeCatalogue (for XML fidelity)
 * 2. External symbol library (fallback)
 */

import { Component } from "./Component";
import {
    SymbolLibraryLoader,
    SymbolEntry,
    ExternalSymbol,
    getGlobalSymbolLibrary
} from "../symbolLibrary";

// Type discriminator for items in store
type ShapeStoreItem = Component | ExternalSymbol;

// Embedded shapes from XML ShapeCatalogue
const shapeCatalogStore = new Map<string, Component>();

// Cached external symbols (loaded from library)
const externalSymbolCache = new Map<string, ExternalSymbol>();

// Configuration
let preferExternalSymbols = true;  // Default: external-first for corporate consistency
let symbolLibraryInitialized = false;

/**
 * Configure whether external symbols are preferred over embedded
 */
export function setPreferExternalSymbols(prefer: boolean): void {
    preferExternalSymbols = prefer;
}

/**
 * Check if external symbols are preferred
 */
export function getPreferExternalSymbols(): boolean {
    return preferExternalSymbols;
}

/**
 * Mark symbol library as initialized (called by server.ts on startup)
 */
export function markSymbolLibraryInitialized(): void {
    symbolLibraryInitialized = true;
}

/**
 * Check if symbol library is ready
 */
export function isSymbolLibraryInitialized(): boolean {
    return symbolLibraryInitialized;
}

/**
 * Add an embedded shape from ShapeCatalogue to the store
 */
export function addToShapeCatalogStore(componentName: string, obj: Component): void {
    shapeCatalogStore.set(componentName, obj);
}

/**
 * Get a shape from the store by component name
 *
 * Lookup order depends on preferExternalSymbols setting:
 * - If true (default): External library → Embedded ShapeCatalogue
 * - If false: Embedded ShapeCatalogue → External library
 *
 * @param componentName - The component/shape name to look up
 * @returns Component, ExternalSymbol, or null if not found
 */
export function getFromShapeCatalogStore<T>(componentName: string): T | null {
    const symbolLibrary = getGlobalSymbolLibrary();

    if (preferExternalSymbols) {
        // External-first: Check symbol library first for corporate consistency
        const external = getExternalSymbol(componentName, symbolLibrary);
        if (external) return external as unknown as T;

        // Fallback to embedded ShapeCatalogue
        const embedded = shapeCatalogStore.get(componentName);
        if (embedded) return embedded as unknown as T;

        return null;
    } else {
        // Embedded-first: Prioritize shapes from the XML itself
        const embedded = shapeCatalogStore.get(componentName);
        if (embedded) return embedded as unknown as T;

        // Fallback to external library
        const external = getExternalSymbol(componentName, symbolLibrary);
        if (external) return external as unknown as T;

        return null;
    }
}

/**
 * Get external symbol from library (with caching)
 */
function getExternalSymbol(
    componentName: string,
    symbolLibrary: SymbolLibraryLoader | null
): ExternalSymbol | null {
    if (!symbolLibrary || !symbolLibrary.isLoaded()) {
        return null;
    }

    // Check cache first
    const cached = externalSymbolCache.get(componentName);
    if (cached) return cached;

    // Look up by DEXPI class first (exact match)
    let entry = symbolLibrary.getByDexpiClass(componentName);

    // If not found, try by identifier
    if (!entry) {
        entry = symbolLibrary.getByIdentifier(componentName);
    }

    // If still not found, try search (partial match)
    if (!entry) {
        entry = symbolLibrary.searchByIdentifier(componentName);
    }

    if (entry) {
        const svgContent = symbolLibrary.loadSvgContent(entry.id);
        if (svgContent) {
            const external = new ExternalSymbol(entry, svgContent);
            if (external.isValid()) {
                externalSymbolCache.set(componentName, external);
                return external;
            } else {
                console.warn(`[ShapeCatalogStore] Invalid external symbol for ${componentName}`);
            }
        } else {
            console.warn(`[ShapeCatalogStore] SVG not found for ${componentName}`);
        }
    }

    return null;
}

/**
 * Check if a component name exists in either store
 */
export function hasInShapeCatalogStore(componentName: string): boolean {
    const symbolLibrary = getGlobalSymbolLibrary();

    // Check embedded
    if (shapeCatalogStore.has(componentName)) return true;

    // Check external cache
    if (externalSymbolCache.has(componentName)) return true;

    // Check external library
    if (symbolLibrary?.isLoaded()) {
        const entry = symbolLibrary.getByDexpiClass(componentName)
            || symbolLibrary.getByIdentifier(componentName);
        if (entry) return true;
    }

    return false;
}

/**
 * Clear the embedded shape catalog store
 * Called between renders to free memory
 */
export function clearShapeCatalogStore(): void {
    shapeCatalogStore.clear();
}

/**
 * Clear the external symbol cache
 * Call between renders to prevent memory leaks
 */
export function clearExternalSymbolCache(): void {
    externalSymbolCache.clear();
}

/**
 * Clear all stores
 */
export function clearAllStores(): void {
    clearShapeCatalogStore();
    clearExternalSymbolCache();
}

/**
 * Get statistics about the stores
 */
export function getStoreStats(): {
    embeddedCount: number;
    externalCacheCount: number;
    preferExternal: boolean;
    libraryInitialized: boolean;
} {
    return {
        embeddedCount: shapeCatalogStore.size,
        externalCacheCount: externalSymbolCache.size,
        preferExternal: preferExternalSymbols,
        libraryInitialized: symbolLibraryInitialized
    };
}

/**
 * Type guard to check if a store item is an ExternalSymbol
 */
export function isExternalSymbol(item: ShapeStoreItem): item is ExternalSymbol {
    return (item as ExternalSymbol).isExternalSymbol === true;
}

/**
 * Type guard to check if a store item is an embedded Component
 */
export function isEmbeddedComponent(item: ShapeStoreItem): item is Component {
    return !isExternalSymbol(item);
}
