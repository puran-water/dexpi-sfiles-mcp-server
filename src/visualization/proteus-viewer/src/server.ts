/**
 * Proteus Viewer - Server-side Rendering Service
 *
 * Provides HTTP API for rendering Proteus XML to SVG format.
 * Uses Paper.js with node-canvas for server-side rendering.
 *
 * Endpoints:
 *   GET /health - Health check
 *   POST /render - Render Proteus XML to SVG
 */

import express, { Request, Response } from 'express';
import { JSDOM } from 'jsdom';
import * as path from 'path';
import { ServerProteusXmlDrawing, renderProteusXML } from './proteusXmlDrawing/ProteusXmlDrawing.server';
import { initGlobalSymbolLibrary } from './symbolLibrary';
import { markSymbolLibraryInitialized, setPreferExternalSymbols } from './proteusXmlDrawing/shapeCatalogStore';

const app = express();

// Initialize symbol library on startup
const catalogPath = path.resolve(__dirname, '../../symbols/assets/merged_catalog.json');
try {
    initGlobalSymbolLibrary(catalogPath);
    markSymbolLibraryInitialized();
    console.log('[Server] Symbol library initialized from:', catalogPath);
} catch (error) {
    console.warn('[Server] Symbol library not available:', error instanceof Error ? error.message : error);
    console.log('[Server] Falling back to embedded ShapeCatalogue only');
}
const PORT = process.env.PROTEUS_VIEWER_PORT || 8081;

// Middleware
app.use(express.json({ limit: '50mb' }));
app.use(express.text({ type: 'application/xml', limit: '50mb' }));

// Health check endpoint
app.get('/health', (_req: Request, res: Response) => {
    const { getStoreStats } = require('./proteusXmlDrawing/shapeCatalogStore');
    const storeStats = getStoreStats();

    res.json({
        status: 'healthy',
        service: 'proteus-viewer',
        version: '0.3.0',
        capabilities: ['svg', 'html', 'png'],
        symbolLibrary: {
            initialized: storeStats.libraryInitialized,
            preferExternal: storeStats.preferExternal,
            embeddedCount: storeStats.embeddedCount,
            externalCacheCount: storeStats.externalCacheCount
        },
        timestamp: new Date().toISOString()
    });
});

// Server info
app.get('/', (_req: Request, res: Response) => {
    res.json({
        name: 'Proteus XML Viewer Service',
        version: '0.1.0',
        endpoints: {
            health: 'GET /health',
            render: 'POST /render'
        }
    });
});

interface RenderRequest {
    xml: string;
    width?: number;
    height?: number;
    format?: 'svg' | 'html' | 'png';
    options?: {
        backgroundColor?: string;
        scale?: number;
        useExternalSymbols?: boolean;  // Use symbol library (default: true)
    };
}

interface RenderResponse {
    success: boolean;
    format: string;
    content?: string;
    error?: string;
    metadata?: {
        width: number;
        height: number;
        schemaVersion?: string;
    };
}

/**
 * Render Proteus XML to SVG
 */
app.post('/render', async (req: Request, res: Response) => {
    try {
        const body = req.body as RenderRequest | string;

        let xml: string;
        let width = 1200;
        let height = 800;
        let format: 'svg' | 'html' | 'png' = 'svg';
        let backgroundColor: string | null = null; // Auto-detect by default

        // Handle both JSON and raw XML
        if (typeof body === 'string') {
            xml = body;
        } else if (body.xml) {
            xml = body.xml;
            width = body.width || width;
            height = body.height || height;
            format = body.format || format;
            backgroundColor = body.options?.backgroundColor || null;

            // Handle useExternalSymbols option - temporarily set preference for this render
            if (body.options?.useExternalSymbols !== undefined) {
                setPreferExternalSymbols(body.options.useExternalSymbols);
            }
        } else {
            return res.status(400).json({
                success: false,
                error: 'Missing XML content. Provide either raw XML or JSON with xml field.'
            } as RenderResponse);
        }

        // Parse XML to get dimensions from Drawing element
        const dom = new JSDOM(xml, { contentType: 'text/xml' });
        const doc = dom.window.document;

        // Check for PlantModel
        const plantModel = doc.getElementsByTagName('PlantModel')[0];
        if (!plantModel) {
            return res.status(400).json({
                success: false,
                error: 'Invalid Proteus XML: Missing PlantModel element'
            } as RenderResponse);
        }

        // Get schema version
        const plantInfo = doc.getElementsByTagName('PlantInformation')[0];
        let schemaVersion: string | undefined = plantInfo?.getAttribute('SchemaVersion') || undefined;

        // Try to get dimensions from Drawing > Extent
        const drawing = doc.getElementsByTagName('Drawing')[0];
        if (drawing) {
            const extent = drawing.getElementsByTagName('Extent')[0];
            if (extent) {
                const max = extent.getElementsByTagName('Max')[0];
                if (max) {
                    const x = parseFloat(max.getAttribute('X') || max.getAttribute('x') || '0');
                    const y = parseFloat(max.getAttribute('Y') || max.getAttribute('y') || '0');
                    if (x > 0) width = Math.ceil(x * 1.5);  // Scale factor
                    if (y > 0) height = Math.ceil(y * 1.5);
                }
            }
        }

        // Standard engineering color scheme: black lines on white background
        // This is the industry standard for P&ID diagrams
        if (!backgroundColor) {
            backgroundColor = '#ffffff'; // White background (engineering standard)
        }

        // Render using the proteusXmlDrawing library
        let svgContent: string;
        let pngBuffer: Buffer | undefined;
        let finalWidth = width;
        let finalHeight = height;

        try {
            // Include PNG if requested
            const includePng = format === 'png';
            console.log(`Render request: format=${format}, includePng=${includePng}, xmlLength=${xml.length}`);
            const result = renderProteusXML(xml, {
                width,
                height,
                backgroundColor
            }, includePng);
            svgContent = result.svg;
            pngBuffer = result.png;
            finalWidth = result.width;
            finalHeight = result.height;
            console.log(`Render result: svgLength=${svgContent.length}, pngBuffer=${pngBuffer ? pngBuffer.length + ' bytes' : 'undefined'}, dimensions=${finalWidth}x${finalHeight}`);
            // Update schemaVersion from result if available
            if (result.schemaVersion) {
                schemaVersion = result.schemaVersion;
            }
        } catch (renderError) {
            console.error('Render error:', renderError);
            // Fallback: return error info as SVG
            svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
                <rect width="100%" height="100%" fill="${backgroundColor}"/>
                <text x="50%" y="50%" text-anchor="middle" fill="red" font-size="16">
                    Render Error: ${renderError instanceof Error ? renderError.message : 'Unknown error'}
                </text>
            </svg>`;
        }

        // Handle PNG format - return base64 encoded
        if (format === 'png' && pngBuffer) {
            return res.json({
                success: true,
                format: 'png',
                content: pngBuffer.toString('base64'),
                metadata: { width: finalWidth, height: finalHeight, schemaVersion }
            } as RenderResponse);
        }

        if (format === 'html') {
            const html = `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Proteus XML Viewer</title>
    <style>
        body { margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f0f0f0; }
        .viewer { background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: auto; max-width: 100vw; max-height: 100vh; }
    </style>
</head>
<body>
    <div class="viewer">
        ${svgContent}
    </div>
</body>
</html>`;
            return res.json({
                success: true,
                format: 'html',
                content: html,
                metadata: { width: finalWidth, height: finalHeight, schemaVersion }
            } as RenderResponse);
        }

        res.json({
            success: true,
            format: 'svg',
            content: svgContent,
            metadata: { width: finalWidth, height: finalHeight, schemaVersion }
        } as RenderResponse);

    } catch (error) {
        console.error('Render error:', error);
        res.status(500).json({
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error'
        } as RenderResponse);
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`Proteus Viewer service running on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/health`);
});

export { app };
