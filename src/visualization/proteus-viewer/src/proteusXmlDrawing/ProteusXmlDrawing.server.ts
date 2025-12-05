/**
 * Server-side Proteus XML Drawing
 * Adapts the browser-based ProteusXmlDrawing for Node.js server-side rendering
 */

import { JSDOM } from "jsdom";
import paper from "paper";
import { createCanvas, Canvas } from "canvas";
import { Resvg } from "@resvg/resvg-js";
import { Component } from "./Component";
import { clearStore } from "./idStore";

// Polyfill for browser globals that the Component code expects
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
(global as any).window = dom.window;
(global as any).document = dom.window.document;
(global as any).DOMParser = dom.window.DOMParser;

export interface ServerRenderOptions {
    width?: number;
    height?: number;
    backgroundColor?: string;
    scale?: number;
    normalizeToBlack?: boolean;  // Convert white/light strokes to black (engineering standard)
}

export interface ServerRenderResult {
    svg: string;
    png?: Buffer;  // PNG as binary buffer
    width: number;
    height: number;
    schemaVersion: string | null;
}

export class ServerProteusXmlDrawing {
    private xml: Document;
    private PlantModel: Component | null = null;
    private canvas: Canvas;
    private width: number;
    private height: number;
    private backgroundColor: string | null = null;
    private normalizeToBlack: boolean = true;  // Default to engineering standard

    constructor(xmlString: string, options: ServerRenderOptions = {}) {
        this.width = options.width || 1200;
        this.height = options.height || 800;

        // Parse XML using DOMParser polyfill
        const parser = new DOMParser();
        this.xml = parser.parseFromString(xmlString, "text/xml");

        // Check for parse errors
        const parseError = this.xml.getElementsByTagName("parsererror")[0];
        if (parseError) {
            throw new Error(`XML Parse Error: ${parseError.textContent}`);
        }

        // Clear any previous state
        clearStore();

        // Initialize Paper.js with node-canvas
        this.canvas = createCanvas(this.width, this.height);
        paper.setup(this.canvas as any);

        // Store background color for use in draw()
        this.backgroundColor = options.backgroundColor || null;

        // Normalize colors to black on white (engineering standard)
        // Default is true unless explicitly set to false
        this.normalizeToBlack = options.normalizeToBlack !== false;

        // Parse PlantModel
        const plantModelElement = this.xml.getElementsByTagName("PlantModel")[0];
        if (!plantModelElement) {
            throw new Error("Invalid Proteus XML: Missing PlantModel element");
        }
        this.PlantModel = new Component(plantModelElement, false);
    }

    public getSchemaLocation(): string | null {
        const plantModelElement = this.xml.getElementsByTagName("PlantModel")[0];
        if (plantModelElement) {
            const schemaLocation = plantModelElement.getAttribute("xsi:schemaLocation");
            if (schemaLocation) {
                return schemaLocation;
            }
            const noNamespaceSchemaLocation = plantModelElement.getAttribute(
                "xsi:noNamespaceSchemaLocation"
            );
            if (noNamespaceSchemaLocation) {
                return noNamespaceSchemaLocation;
            }
        }
        return null;
    }

    public getSchemaVersion(): string | null {
        const PlantInformation = this.xml.getElementsByTagName("PlantInformation")[0];
        if (PlantInformation) {
            const schemaVersion = PlantInformation.getAttribute("SchemaVersion");
            if (schemaVersion) {
                return schemaVersion;
            }
        }
        return null;
    }

    /**
     * Draw the Proteus XML to the Paper.js canvas
     */
    public draw(): void {
        if (!this.PlantModel) {
            throw new Error("PlantModel not initialized");
        }

        // Clear before drawing
        paper.project.activeLayer.removeChildren();

        // Add background if specified
        if (this.backgroundColor) {
            new paper.Path.Rectangle({
                point: [0, 0],
                size: [this.width, this.height],
                fillColor: new paper.Color(this.backgroundColor)
            });
        }

        const unitTypesSupported = ["Metre", "mm", "Millimetre", "m"];
        const PlantInfo = (this.PlantModel as any).PlantInformation?.[0];
        const PlantInformationUnitType = PlantInfo?.units?.value || "mm";

        let unit = 1.5;
        switch (PlantInformationUnitType) {
            case "Metre":
            case "m":
                unit = 1500;
                break;
        }

        // Get drawing dimensions
        const PlantModelAny = this.PlantModel as any;
        const drawing = PlantModelAny.Drawing?.[0];

        let x: number;
        let y: number;

        if (drawing?.Extent?.[0]?.Max?.[0]) {
            x = drawing.Extent[0].Max[0].x?.valueAsNumber || this.width / unit;
            y = drawing.Extent[0].Max[0].y?.valueAsNumber || this.height / unit;
        } else if (PlantModelAny.Extent?.[0]?.Max?.[0]) {
            x = PlantModelAny.Extent[0].Max[0].x?.valueAsNumber || this.width / unit;
            y = PlantModelAny.Extent[0].Max[0].y?.valueAsNumber || this.height / unit;
        } else {
            // Default dimensions
            x = unit === 1.5 ? 1261.5 : 0.12615;
            y = unit === 1.5 ? 891 : 0.891;
        }

        // Resize canvas to match content
        const scaledWidth = Math.ceil(x * unit);
        const scaledHeight = Math.ceil(y * unit);

        if (scaledWidth > 0 && scaledHeight > 0) {
            this.width = scaledWidth;
            this.height = scaledHeight;
            // Note: node-canvas doesn't support resize, so we use initial dimensions
        }

        // Draw the model - using a stub proteusXmlDrawing object for event handling
        const stubDrawing = {
            publicEvent: (_name: string, _data: any) => {
                // Server-side rendering doesn't need event handling
            }
        };

        PlantModelAny.draw(unit, x, y, 0, 0, null, this.PlantModel, stubDrawing);
    }

    /**
     * Check if a color is light (close to white)
     */
    private isLightColor(color: string): boolean {
        // Handle hex colors
        if (color.startsWith('#')) {
            const hex = color.slice(1);
            let r: number, g: number, b: number;
            if (hex.length === 3) {
                r = parseInt(hex[0] + hex[0], 16);
                g = parseInt(hex[1] + hex[1], 16);
                b = parseInt(hex[2] + hex[2], 16);
            } else if (hex.length === 6) {
                r = parseInt(hex.slice(0, 2), 16);
                g = parseInt(hex.slice(2, 4), 16);
                b = parseInt(hex.slice(4, 6), 16);
            } else {
                return false;
            }
            // Consider light if all components > 200 (close to white)
            return r > 200 && g > 200 && b > 200;
        }
        // Handle rgb/rgba
        const rgbMatch = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (rgbMatch) {
            const r = parseInt(rgbMatch[1]);
            const g = parseInt(rgbMatch[2]);
            const b = parseInt(rgbMatch[3]);
            return r > 200 && g > 200 && b > 200;
        }
        // Handle named colors
        if (color.toLowerCase() === 'white') return true;
        return false;
    }

    /**
     * Normalize SVG colors to black on white (engineering standard)
     */
    private normalizeColors(svgString: string): string {
        // Light colors to replace with black (for strokes and fills that aren't backgrounds)
        const lightColors = [
            '#ffffff', '#FFFFFF', '#fff', '#FFF',
            '#fefefe', '#FEFEFE', '#fafafa', '#FAFAFA',
            '#f0f0f0', '#F0F0F0', '#eeeeee', '#EEEEEE',
            'white', 'rgb(255,255,255)', 'rgb(255, 255, 255)',
            'rgba(255,255,255,1)', 'rgba(255, 255, 255, 1)'
        ];

        let result = svgString;

        // Replace stroke colors (but not fill for backgrounds)
        for (const lightColor of lightColors) {
            // Replace stroke="lightColor" with stroke="#000000"
            result = result.replace(
                new RegExp(`stroke="${lightColor}"`, 'gi'),
                'stroke="#000000"'
            );
            // Replace stroke:lightColor in style attributes
            result = result.replace(
                new RegExp(`stroke:\\s*${lightColor.replace(/[()]/g, '\\$&')}`, 'gi'),
                'stroke:#000000'
            );
        }

        // Replace fill colors for text and shapes (but preserve background rectangles)
        // Look for fill on non-background elements (text, paths that aren't the first child)
        for (const lightColor of lightColors) {
            // Replace fill="lightColor" on text elements
            result = result.replace(
                new RegExp(`(<text[^>]*)fill="${lightColor}"`, 'gi'),
                '$1fill="#000000"'
            );
            // Replace fill in style for text
            result = result.replace(
                new RegExp(`(<text[^>]*style="[^"]*)fill:\\s*${lightColor.replace(/[()]/g, '\\$&')}`, 'gi'),
                '$1fill:#000000'
            );
        }

        return result;
    }

    /**
     * Export the rendered drawing to SVG
     */
    public exportSVG(): string {
        // Get the bounds of all content in the project
        const bounds = paper.project.activeLayer.bounds;

        // Export SVG with proper bounds
        const svgElement = paper.project.exportSVG({
            asString: false,
            bounds: bounds.isEmpty() ? new paper.Rectangle(0, 0, this.width, this.height) : bounds
        }) as SVGElement;

        // Set proper viewBox and dimensions on the SVG
        if (!bounds.isEmpty()) {
            svgElement.setAttribute('width', String(Math.ceil(bounds.width)));
            svgElement.setAttribute('height', String(Math.ceil(bounds.height)));
            svgElement.setAttribute('viewBox', `${Math.floor(bounds.x)},${Math.floor(bounds.y)},${Math.ceil(bounds.width)},${Math.ceil(bounds.height)}`);
        } else {
            svgElement.setAttribute('width', String(this.width));
            svgElement.setAttribute('height', String(this.height));
            svgElement.setAttribute('viewBox', `0,0,${this.width},${this.height}`);
        }

        // Convert to string using XMLSerializer
        const serializer = new (global as any).window.XMLSerializer();
        let svgString = serializer.serializeToString(svgElement);

        // Normalize colors to black on white if enabled (engineering standard)
        if (this.normalizeToBlack) {
            svgString = this.normalizeColors(svgString);
        }

        return svgString;
    }

    /**
     * Export the rendered drawing to PNG using resvg-js
     * First exports to SVG, then converts to PNG for reliable rasterization
     */
    public exportPNG(): Buffer {
        // First get the SVG
        const svgString = this.exportSVG();

        // Use resvg-js to convert SVG to PNG
        const resvg = new Resvg(svgString, {
            background: '#ffffff', // White background (engineering standard)
            fitTo: {
                mode: 'original'
            }
        });

        const pngData = resvg.render();
        return Buffer.from(pngData.asPng());
    }

    /**
     * Render and return the result
     */
    public render(includePng: boolean = false): ServerRenderResult {
        this.draw();
        const svg = this.exportSVG();
        const png = includePng ? this.exportPNG() : undefined;

        // Clear project after export
        paper.project.clear();

        return {
            svg,
            png,
            width: this.width,
            height: this.height,
            schemaVersion: this.getSchemaVersion()
        };
    }
}

/**
 * Render Proteus XML to SVG (and optionally PNG) in one call
 */
export function renderProteusXML(
    xmlString: string,
    options: ServerRenderOptions = {},
    includePng: boolean = false
): ServerRenderResult {
    const drawing = new ServerProteusXmlDrawing(xmlString, options);
    return drawing.render(includePng);
}
