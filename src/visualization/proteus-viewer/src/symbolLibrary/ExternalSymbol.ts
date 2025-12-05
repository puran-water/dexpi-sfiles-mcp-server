/**
 * ExternalSymbol - Component-compatible wrapper for external symbol library symbols
 *
 * This class provides a draw() interface compatible with the existing Component system
 * in proteusXmlDrawing, allowing external symbols to be used as drop-in replacements
 * for embedded ShapeCatalogue shapes.
 */

import paper from 'paper';
import { SymbolEntry, PortDefinition, BoundingBox, AnchorPoint } from './SymbolLibraryLoader';
import { svgToPaperJsGroup, cloneForPlacement, applyTransforms, normalizeColors } from './SvgToPaperJs';

/**
 * ExternalSymbol wraps a symbol from our external library to be compatible
 * with the Component draw() interface used by proteusXmlDrawing
 */
export class ExternalSymbol {
    /** Type discriminator to differentiate from XML Components */
    public readonly isExternalSymbol: boolean = true;

    /** Symbol entry from catalog */
    private symbolEntry: SymbolEntry;

    /** Paper.js Group template - NEVER modify directly, always clone */
    private svgTemplate: paper.Group | null = null;

    /** Extent for debug overlays - mirrors Component structure */
    public Extent?: {
        Min?: Array<{ x?: { valueAsNumber: number }; y?: { valueAsNumber: number } }>;
        Max?: Array<{ x?: { valueAsNumber: number }; y?: { valueAsNumber: number } }>;
    };

    /** ComponentName for lookup compatibility */
    public ComponentName?: string;

    /**
     * Create an ExternalSymbol from a catalog entry and SVG content
     *
     * @param entry - Symbol entry from merged_catalog.json
     * @param svgContent - SVG string content for the symbol
     */
    constructor(entry: SymbolEntry, svgContent: string) {
        this.symbolEntry = entry;
        this.ComponentName = entry.id;

        // Import SVG to Paper.js - this is our template
        try {
            this.svgTemplate = svgToPaperJsGroup(svgContent, {
                expandShapes: true,
                insert: false,
                applyMatrix: false
            });

            // Normalize colors to engineering standard (black on white)
            normalizeColors(this.svgTemplate);
        } catch (error) {
            console.error(`[ExternalSymbol] Failed to import SVG for ${entry.id}:`, error);
            this.svgTemplate = null;
        }

        // Set up Extent for debug overlays (mirrors Component structure)
        this.Extent = this.computeExtent(entry.bounding_box);
    }

    /**
     * Compute Extent from bounding box (mirrors Component Extent structure)
     */
    private computeExtent(bbox: BoundingBox): ExternalSymbol['Extent'] {
        return {
            Min: [{
                x: { valueAsNumber: bbox.x },
                y: { valueAsNumber: bbox.y }
            }],
            Max: [{
                x: { valueAsNumber: bbox.x + bbox.width },
                y: { valueAsNumber: bbox.y + bbox.height }
            }]
        };
    }

    /**
     * Get the symbol entry metadata
     */
    public getSymbolEntry(): SymbolEntry {
        return this.symbolEntry;
    }

    /**
     * Get port definitions for this symbol
     */
    public getPorts(): PortDefinition[] {
        return this.symbolEntry.ports || [];
    }

    /**
     * Get the anchor point
     */
    public getAnchorPoint(): AnchorPoint {
        return this.symbolEntry.anchor_point;
    }

    /**
     * Get the bounding box
     */
    public getBoundingBox(): BoundingBox {
        return this.symbolEntry.bounding_box;
    }

    /**
     * Check if SVG was loaded successfully
     */
    public isValid(): boolean {
        return this.svgTemplate !== null;
    }

    /**
     * Component-compatible draw interface
     *
     * This method follows the same signature as Component.draw() from proteusXmlDrawing,
     * allowing ExternalSymbol to be used as a drop-in replacement.
     *
     * @param unit - Scale factor (based on PlantInformation units)
     * @param pageOriginX - Page X origin offset
     * @param pageOriginY - Page Y origin offset
     * @param offsetX - Additional X offset
     * @param offsetY - Additional Y offset
     * @param group - Parent Paper.js Group to add this symbol to
     * @param caller - The Component that called draw (contains Position, Scale, etc.)
     * @param proteusXmlDrawing - Reference to ProteusXmlDrawing for events
     */
    public draw(
        unit: number,
        pageOriginX: number,
        pageOriginY: number,
        offsetX: number,
        offsetY: number,
        group: paper.Group | null,
        caller: any,
        proteusXmlDrawing: any
    ): void {
        if (!this.svgTemplate) {
            console.warn(`[ExternalSymbol] Cannot draw ${this.symbolEntry.id}: SVG not loaded`);
            return;
        }

        // CRITICAL: Clone template to avoid cross-instance mutations
        const clone = cloneForPlacement(this.svgTemplate);

        // Get anchor point from catalog
        const anchor = this.symbolEntry.anchor_point;

        // Get position from caller (Position element in XML)
        const pos = caller?.Position?.[0];
        const posX = (pos?.x?.valueAsNumber || 0);
        const posY = (pos?.y?.valueAsNumber || 0);

        // Get scale from caller (Scale element in XML)
        const scale = caller?.Scale?.[0];
        const scaleX = scale?.x?.valueAsNumber ?? 1;
        const scaleY = scale?.y?.valueAsNumber ?? 1;

        // Get rotation from Reference/Axis elements
        const rotation = this.getRotationFromCaller(caller);
        const flipY = this.getYFlipFromCaller(caller);

        // Calculate final position
        // Transform order: anchor alignment → unit scale → position → rotation/flip
        // Note: Proteus uses Y-up coordinate system, Paper.js uses Y-down

        // 1. Start with clone at origin
        // 2. Apply anchor alignment - offset so anchor_point sits at (0,0)
        clone.translate(new paper.Point(-anchor.x, -anchor.y));

        // 3. Apply scale from XML (if different from 1)
        if (scaleX !== 1 || scaleY !== 1) {
            clone.scale(scaleX, scaleY, new paper.Point(0, 0));
        }

        // 4. Apply rotation around the anchor point (now at origin)
        if (rotation !== 0) {
            clone.rotate(rotation, new paper.Point(0, 0));
        }

        // 5. Apply Y-flip if needed (for mirrored symbols)
        if (flipY) {
            clone.scale(1, -1, new paper.Point(0, 0));
        }

        // 6. Apply unit scaling (symbol library uses mm)
        clone.scale(unit);

        // 7. Translate to final position
        // Note: Proteus Y-coordinates need to be flipped for Paper.js canvas
        const finalX = posX * unit + pageOriginX + offsetX;
        const finalY = posY * unit + pageOriginY + offsetY;
        clone.translate(new paper.Point(finalX, finalY));

        // Wire up click event for consistency with XML shapes
        clone.onClick = () => {
            if (proteusXmlDrawing?.publicEvent) {
                proteusXmlDrawing.publicEvent('onClick', {
                    component: caller,
                    symbolEntry: this.symbolEntry,
                    isExternalSymbol: true
                });
            }
        };

        // Add to parent group or active layer
        if (group) {
            group.addChild(clone);
        } else {
            paper.project.activeLayer.addChild(clone);
        }
    }

    /**
     * Extract rotation angle from caller's Reference/Axis elements
     */
    private getRotationFromCaller(caller: any): number {
        // Check for Axis element (defines local coordinate system)
        const axis = caller?.Axis?.[0];
        if (axis) {
            const refX = axis.x?.valueAsNumber ?? 1;
            const refY = axis.y?.valueAsNumber ?? 0;

            // Calculate angle from axis vector
            // Default axis is (1, 0) = 0 degrees
            if (refX !== 0 || refY !== 0) {
                const angle = Math.atan2(refY, refX) * (180 / Math.PI);
                return angle;
            }
        }

        // Check for Reference element (alternative rotation specification)
        const reference = caller?.Reference?.[0];
        if (reference) {
            const refX = reference.x?.valueAsNumber ?? 1;
            const refY = reference.y?.valueAsNumber ?? 0;

            if (refX !== 0 || refY !== 0) {
                const angle = Math.atan2(refY, refX) * (180 / Math.PI);
                return angle;
            }
        }

        return 0;
    }

    /**
     * Check if Y-flip is needed from caller's Reference/Axis elements
     */
    private getYFlipFromCaller(caller: any): boolean {
        // Check for Axis element with Y component indicating flip
        const axis = caller?.Axis?.[0];
        if (axis) {
            // If Y component of reference vector is negative while X is positive,
            // it might indicate a flip
            const orientation = axis.Orientation?.value;
            if (orientation === 'clockwise' || orientation === 'flipped') {
                return true;
            }
        }

        // Check for explicit flip attribute
        const presentation = caller?.Presentation?.[0];
        if (presentation?.FlipY?.value === 'true' || presentation?.flipY === true) {
            return true;
        }

        return false;
    }

    /**
     * Create a placeholder symbol for when SVG fails to load
     * Returns a simple rectangle with an X through it
     */
    public static createPlaceholder(entry: SymbolEntry): ExternalSymbol {
        // Create minimal SVG placeholder
        const bbox = entry.bounding_box;
        const placeholderSvg = `
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="${bbox.width}" height="${bbox.height}"
                 viewBox="${bbox.x} ${bbox.y} ${bbox.width} ${bbox.height}">
                <rect x="${bbox.x}" y="${bbox.y}"
                      width="${bbox.width}" height="${bbox.height}"
                      stroke="#ff0000" stroke-width="0.5" fill="none"/>
                <line x1="${bbox.x}" y1="${bbox.y}"
                      x2="${bbox.x + bbox.width}" y2="${bbox.y + bbox.height}"
                      stroke="#ff0000" stroke-width="0.25"/>
                <line x1="${bbox.x + bbox.width}" y1="${bbox.y}"
                      x2="${bbox.x}" y2="${bbox.y + bbox.height}"
                      stroke="#ff0000" stroke-width="0.25"/>
            </svg>
        `;

        return new ExternalSymbol(entry, placeholderSvg);
    }
}
