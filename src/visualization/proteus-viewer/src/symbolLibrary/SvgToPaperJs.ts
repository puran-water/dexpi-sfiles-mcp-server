/**
 * SVG to Paper.js Converter
 * Converts SVG string content to Paper.js Group objects for rendering
 */

import paper from 'paper';

/**
 * Options for SVG import
 */
export interface SvgImportOptions {
    /** Whether to expand compound shapes (default: true) */
    expandShapes?: boolean;
    /** Whether to auto-insert into active layer (default: false) */
    insert?: boolean;
    /** Apply transformations directly to path data (default: false) */
    applyMatrix?: boolean;
}

/**
 * Import SVG content string into a Paper.js Group
 *
 * IMPORTANT: This creates a template that should be cloned before applying transforms.
 * Never modify the returned Group directly if reusing - use svgTemplate.clone() first.
 *
 * @param svgContent - The SVG string content to import
 * @param options - Import options
 * @returns Paper.js Group containing the imported SVG elements
 */
export function svgToPaperJsGroup(svgContent: string, options: SvgImportOptions = {}): paper.Group {
    const importOptions = {
        expandShapes: options.expandShapes !== false,  // Default true
        insert: options.insert === true,               // Default false - caller manages
        applyMatrix: options.applyMatrix === true      // Default false
    };

    // Preprocess SVG to handle common issues
    let processedSvg = preprocessSvg(svgContent);

    // Import using Paper.js
    const imported = paper.project.importSVG(processedSvg, importOptions);

    if (!imported) {
        throw new Error('Failed to import SVG: importSVG returned null');
    }

    // Ensure we return a Group
    if (imported instanceof paper.Group) {
        return imported;
    } else {
        // Wrap in a group if it's a single item
        const group = new paper.Group([imported]);
        return group;
    }
}

/**
 * Preprocess SVG to fix common issues before Paper.js import
 */
function preprocessSvg(svgContent: string): string {
    let result = svgContent;

    // Remove XML declaration if present (Paper.js handles this but cleaner without)
    result = result.replace(/<\?xml[^>]*\?>/gi, '');

    // Remove DOCTYPE if present
    result = result.replace(/<!DOCTYPE[^>]*>/gi, '');

    // Remove comments
    result = result.replace(/<!--[\s\S]*?-->/g, '');

    // Remove external references (fonts, images) that could cause issues
    // Replace external fonts with generic fallback
    result = result.replace(/font-family\s*:\s*['"][^'"]+['"]/gi, 'font-family: sans-serif');
    result = result.replace(/font-family\s*=\s*['"][^'"]+['"]/gi, 'font-family="sans-serif"');

    // Remove xlink:href to external images
    result = result.replace(/xlink:href\s*=\s*['"][^'"]+\.(png|jpg|jpeg|gif|bmp)['"]/gi, 'xlink:href=""');
    result = result.replace(/href\s*=\s*['"][^'"]+\.(png|jpg|jpeg|gif|bmp)['"]/gi, 'href=""');

    // Ensure SVG namespace is present
    if (!result.includes('xmlns="http://www.w3.org/2000/svg"') && !result.includes("xmlns='http://www.w3.org/2000/svg'")) {
        result = result.replace(/<svg\s/i, '<svg xmlns="http://www.w3.org/2000/svg" ');
    }

    return result.trim();
}

/**
 * Clone a Paper.js Group safely for use with transforms
 *
 * This is the recommended way to use imported SVG templates:
 * 1. Import once with svgToPaperJsGroup() and store as template
 * 2. Clone the template for each placement with cloneForPlacement()
 * 3. Apply transforms to the clone, not the template
 *
 * @param template - The original Paper.js Group to clone
 * @returns A deep clone of the group
 */
export function cloneForPlacement(template: paper.Group): paper.Group {
    return template.clone({ insert: false, deep: true });
}

/**
 * Apply common transforms to a Paper.js Group
 * Follows engineering P&ID transform order: translate → scale → rotate
 *
 * @param group - The Paper.js Group to transform
 * @param options - Transform options
 */
export interface TransformOptions {
    /** Translation in x */
    translateX?: number;
    /** Translation in y */
    translateY?: number;
    /** Scale factor for x (default: 1) */
    scaleX?: number;
    /** Scale factor for y (default: 1) */
    scaleY?: number;
    /** Rotation in degrees */
    rotation?: number;
    /** Y-axis flip (mirror vertically) */
    flipY?: boolean;
    /** X-axis flip (mirror horizontally) */
    flipX?: boolean;
    /** Anchor point for rotation and scaling */
    anchor?: paper.Point;
}

export function applyTransforms(group: paper.Group, options: TransformOptions): void {
    // 1. Apply translation
    if (options.translateX !== undefined || options.translateY !== undefined) {
        group.translate(new paper.Point(
            options.translateX || 0,
            options.translateY || 0
        ));
    }

    // 2. Apply scale
    const scaleX = options.scaleX ?? 1;
    const scaleY = options.scaleY ?? 1;
    if (scaleX !== 1 || scaleY !== 1) {
        const anchor = options.anchor || group.bounds.center;
        group.scale(scaleX, scaleY, anchor);
    }

    // 3. Apply flip (as special scale)
    if (options.flipY) {
        const anchor = options.anchor || group.bounds.center;
        group.scale(1, -1, anchor);
    }
    if (options.flipX) {
        const anchor = options.anchor || group.bounds.center;
        group.scale(-1, 1, anchor);
    }

    // 4. Apply rotation
    if (options.rotation !== undefined && options.rotation !== 0) {
        const anchor = options.anchor || group.bounds.center;
        group.rotate(options.rotation, anchor);
    }
}

/**
 * Normalize colors in a Paper.js Group to engineering standard (black on white)
 *
 * @param group - The Paper.js Group to normalize
 * @param strokeColor - Target stroke color (default: black)
 * @param preserveFills - Whether to preserve fill colors (default: false)
 */
export function normalizeColors(
    group: paper.Group,
    strokeColor: string = '#000000',
    preserveFills: boolean = false
): void {
    const targetStroke = new paper.Color(strokeColor);

    function processItem(item: paper.Item): void {
        if (item instanceof paper.Group) {
            item.children.forEach(child => processItem(child));
        } else if (item instanceof paper.Path || item instanceof paper.CompoundPath) {
            // Check if stroke is light (close to white)
            if (item.strokeColor) {
                const color = item.strokeColor as paper.Color;
                if (isLightColor(color)) {
                    item.strokeColor = targetStroke;
                }
            }
            // Normalize fill for non-background elements if not preserving
            if (!preserveFills && item.fillColor) {
                const color = item.fillColor as paper.Color;
                if (isLightColor(color)) {
                    item.fillColor = targetStroke;
                }
            }
        } else if (item instanceof paper.PointText) {
            // Normalize text color
            if (item.fillColor) {
                const color = item.fillColor as paper.Color;
                if (isLightColor(color)) {
                    item.fillColor = targetStroke;
                }
            }
        }
    }

    processItem(group);
}

/**
 * Check if a color is considered "light" (close to white)
 */
function isLightColor(color: paper.Color): boolean {
    if (!color) return false;

    // Get RGB components (0-1 range)
    const r = color.red ?? 0;
    const g = color.green ?? 0;
    const b = color.blue ?? 0;

    // Consider light if all components > 0.78 (200/255)
    return r > 0.78 && g > 0.78 && b > 0.78;
}

/**
 * Get the bounds of a Paper.js Group in its local coordinate system
 */
export function getLocalBounds(group: paper.Group): paper.Rectangle {
    return group.bounds;
}

/**
 * Utility to set stroke weight uniformly
 */
export function setStrokeWeight(group: paper.Group, weight: number): void {
    function processItem(item: paper.Item): void {
        if (item instanceof paper.Group) {
            item.children.forEach(child => processItem(child));
        } else if (item instanceof paper.Path || item instanceof paper.CompoundPath) {
            item.strokeWidth = weight;
        }
    }
    processItem(group);
}
