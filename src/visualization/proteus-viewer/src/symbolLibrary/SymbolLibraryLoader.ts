/**
 * Symbol Library Loader
 * Loads merged_catalog.json and provides symbol lookup by DEXPI class or identifier
 */

import * as fs from 'fs';
import * as path from 'path';

// Port definition from catalog
export interface PortDefinition {
    id: string;
    x: number;
    y: number;
    direction: string;  // 'left', 'right', 'top', 'bottom'
    type: string;       // 'process', 'instrument', etc.
}

// Bounding box definition
export interface BoundingBox {
    x: number;
    y: number;
    width: number;
    height: number;
}

// Anchor point definition
export interface AnchorPoint {
    x: number;
    y: number;
}

// Symbol entry from merged_catalog.json
export interface SymbolEntry {
    id: string;
    name: string;
    category: string;
    dexpi_class: string | null;
    source_file: string;
    provenance?: {
        original_file: string;
        catalog_name: string;
        extraction_date: string;
    };
    metadata?: Record<string, any>;
    bounding_box: BoundingBox;
    anchor_point: AnchorPoint;
    ports?: PortDefinition[];
    scalable: boolean;
    rotatable: boolean;
}

// Catalog structure from merged_catalog.json
interface CatalogFile {
    version: string;
    generated: string;
    statistics: {
        total_symbols: number;
        by_category: Record<string, number>;
        by_catalog: Record<string, number>;
    };
    symbols: Record<string, SymbolEntry>;
}

export class SymbolLibraryLoader {
    private catalog: Map<string, SymbolEntry> = new Map();         // id -> symbol
    private byDexpiClass: Map<string, SymbolEntry[]> = new Map();  // dexpi_class -> symbols (may have variants)
    private svgCache: Map<string, string> = new Map();             // symbol_id -> svg_content
    private catalogBasePath: string = '';
    private loaded: boolean = false;

    /**
     * Load the catalog from merged_catalog.json
     */
    public loadCatalog(catalogPath: string): void {
        if (!fs.existsSync(catalogPath)) {
            throw new Error(`Symbol catalog not found: ${catalogPath}`);
        }

        const catalogContent = fs.readFileSync(catalogPath, 'utf-8');
        const catalogData: CatalogFile = JSON.parse(catalogContent);

        // Store base path for SVG loading
        this.catalogBasePath = path.dirname(catalogPath);

        // Index symbols
        for (const [id, entry] of Object.entries(catalogData.symbols)) {
            // Ensure id is set (it should match the key)
            entry.id = id;
            this.catalog.set(id, entry);

            // Index by DEXPI class if available
            if (entry.dexpi_class) {
                const existing = this.byDexpiClass.get(entry.dexpi_class) || [];
                existing.push(entry);
                this.byDexpiClass.set(entry.dexpi_class, existing);
            }
        }

        this.loaded = true;
        console.log(`[SymbolLibrary] Loaded ${this.catalog.size} symbols, ${this.byDexpiClass.size} DEXPI classes`);
    }

    /**
     * Get symbol by DEXPI class name
     * Returns the "standard" variant (non-Detail, non-Option) if multiple exist
     */
    public getByDexpiClass(dexpiClass: string): SymbolEntry | null {
        if (!this.loaded) {
            console.warn('[SymbolLibrary] Catalog not loaded');
            return null;
        }

        const variants = this.byDexpiClass.get(dexpiClass);
        if (!variants || variants.length === 0) {
            return null;
        }

        // Prefer standard variant (no suffix like _Detail, _Option, _Origo)
        const standard = variants.find(v =>
            !v.id.includes('_Detail') &&
            !v.id.includes('_Option') &&
            !v.id.includes('_Origo')
        );

        return standard || variants[0];
    }

    /**
     * Get all variants for a DEXPI class
     */
    public getAllVariantsByDexpiClass(dexpiClass: string): SymbolEntry[] {
        if (!this.loaded) {
            console.warn('[SymbolLibrary] Catalog not loaded');
            return [];
        }

        return this.byDexpiClass.get(dexpiClass) || [];
    }

    /**
     * Get symbol by exact identifier (id)
     */
    public getByIdentifier(identifier: string): SymbolEntry | null {
        if (!this.loaded) {
            console.warn('[SymbolLibrary] Catalog not loaded');
            return null;
        }

        return this.catalog.get(identifier) || null;
    }

    /**
     * Search for symbol by partial identifier match
     * Useful when componentName doesn't exactly match catalog id
     */
    public searchByIdentifier(searchTerm: string): SymbolEntry | null {
        if (!this.loaded) {
            console.warn('[SymbolLibrary] Catalog not loaded');
            return null;
        }

        // Exact match first
        const exact = this.catalog.get(searchTerm);
        if (exact) return exact;

        // Case-insensitive match
        const searchLower = searchTerm.toLowerCase();
        for (const [id, entry] of this.catalog.entries()) {
            if (id.toLowerCase() === searchLower) {
                return entry;
            }
        }

        // Partial match (contains)
        for (const [id, entry] of this.catalog.entries()) {
            if (id.toLowerCase().includes(searchLower) ||
                searchLower.includes(id.toLowerCase())) {
                return entry;
            }
        }

        return null;
    }

    /**
     * Load SVG content for a symbol
     * Caches loaded SVGs for reuse
     */
    public loadSvgContent(symbolId: string): string | null {
        // Check cache first
        const cached = this.svgCache.get(symbolId);
        if (cached) return cached;

        const entry = this.catalog.get(symbolId);
        if (!entry) {
            console.warn(`[SymbolLibrary] Symbol not found: ${symbolId}`);
            return null;
        }

        // Build SVG path from source_file
        // source_file is like "NOAKADEXPI/Detail/ND0009_Detail.svg"
        const svgPath = path.join(this.catalogBasePath, entry.source_file);

        if (!fs.existsSync(svgPath)) {
            console.warn(`[SymbolLibrary] SVG file not found: ${svgPath}`);
            return null;
        }

        const svgContent = fs.readFileSync(svgPath, 'utf-8');
        this.svgCache.set(symbolId, svgContent);

        return svgContent;
    }

    /**
     * Clear SVG cache to free memory
     */
    public clearSvgCache(): void {
        this.svgCache.clear();
    }

    /**
     * Get catalog statistics
     */
    public getStats(): { total: number; withDexpiClass: number; svgCacheSize: number } {
        return {
            total: this.catalog.size,
            withDexpiClass: this.byDexpiClass.size,
            svgCacheSize: this.svgCache.size
        };
    }

    /**
     * Check if catalog is loaded
     */
    public isLoaded(): boolean {
        return this.loaded;
    }

    /**
     * Get all available DEXPI classes
     */
    public getAvailableDexpiClasses(): string[] {
        return Array.from(this.byDexpiClass.keys());
    }

    /**
     * Get all symbol IDs
     */
    public getAllSymbolIds(): string[] {
        return Array.from(this.catalog.keys());
    }
}

// Singleton instance for shared use
let globalLoader: SymbolLibraryLoader | null = null;

export function getGlobalSymbolLibrary(): SymbolLibraryLoader | null {
    return globalLoader;
}

export function initGlobalSymbolLibrary(catalogPath: string): SymbolLibraryLoader {
    globalLoader = new SymbolLibraryLoader();
    globalLoader.loadCatalog(catalogPath);
    return globalLoader;
}

export function clearGlobalSymbolLibrary(): void {
    if (globalLoader) {
        globalLoader.clearSvgCache();
        globalLoader = null;
    }
}
