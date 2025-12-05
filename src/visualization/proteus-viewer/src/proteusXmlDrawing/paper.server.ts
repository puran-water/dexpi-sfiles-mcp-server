/**
 * Server-side Paper.js initialization for Node.js
 * Uses node-canvas instead of HTML canvas
 */

import paper from "paper";
import { createCanvas, Canvas } from "canvas";

let serverCanvas: Canvas | null = null;

export function getPaper() {
    return paper;
}

export type PaperGroup = paper.Group;

/**
 * Initialize Paper.js with a node-canvas for server-side rendering
 * @param width Canvas width
 * @param height Canvas height
 * @returns The node-canvas instance
 */
export function initServerPaper(width: number, height: number): Canvas {
    serverCanvas = createCanvas(width, height);
    paper.setup(serverCanvas as any);
    return serverCanvas;
}

/**
 * Get the current server canvas
 */
export function getServerCanvas(): Canvas | null {
    return serverCanvas;
}

/**
 * Export the current Paper.js project to SVG
 */
export function exportToSVG(): string {
    const svg = paper.project.exportSVG({ asString: true }) as string;
    return svg;
}

/**
 * Clear the Paper.js project
 */
export function clearProject() {
    paper.project.clear();
}
