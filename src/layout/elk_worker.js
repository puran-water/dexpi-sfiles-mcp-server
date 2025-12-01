#!/usr/bin/env node
/**
 * ELK Layout Worker - Persistent Process
 *
 * Long-running Node.js process that handles ELK layout requests.
 * Communicates via newline-delimited JSON over stdin/stdout.
 *
 * Architecture Decision (Codex Consensus #019adb91):
 * - Persistent worker (not per-call spawn) for performance
 * - stdin/stdout JSON protocol with request IDs
 * - Request format: {"id": "...", "graph": {...}}
 * - Response format: {"id": "...", "result": {...}} or {"id": "...", "error": "..."}
 * - Proper error handling with stderr for logging
 *
 * Usage:
 *   # Start persistent worker
 *   node elk_worker.js
 *
 *   # Send request (newline-delimited JSON)
 *   {"id":"req-1","graph":{"id":"root","children":[...]}}
 *
 *   # Receive response
 *   {"id":"req-1","result":{"id":"root","children":[...],"x":0,"y":0}}
 */

const ELK = require('elkjs');
const readline = require('readline');

// Create ELK instance once (reused across requests)
const elk = new ELK();

// Track request count for logging
let requestCount = 0;

/**
 * Process a single layout request.
 * @param {Object} request - Request with id and graph
 * @returns {Object} Response with id and result/error
 */
async function processRequest(request) {
    const { id, graph } = request;
    requestCount++;

    if (!id) {
        return { error: 'Missing request id' };
    }

    if (!graph) {
        return { id, error: 'Missing graph in request' };
    }

    try {
        const result = await elk.layout(graph);
        return { id, result };
    } catch (e) {
        return { id, error: e.message || 'ELK layout failed' };
    }
}

/**
 * Main loop - reads requests from stdin, writes responses to stdout.
 */
async function main() {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
        terminal: false
    });

    // Log startup to stderr (not stdout to keep protocol clean)
    console.error(`ELK worker started (PID: ${process.pid})`);

    // Process each line as a JSON request
    for await (const line of rl) {
        if (!line.trim()) continue;

        let request;
        try {
            request = JSON.parse(line);
        } catch (e) {
            // Invalid JSON - respond with error
            const response = { error: `Invalid JSON: ${e.message}` };
            console.log(JSON.stringify(response));
            continue;
        }

        // Process request and send response
        const response = await processRequest(request);
        console.log(JSON.stringify(response));
    }

    // Log shutdown
    console.error(`ELK worker shutting down after ${requestCount} requests`);
}

// Handle uncaught errors gracefully
process.on('uncaughtException', (err) => {
    console.error(`ELK worker uncaught exception: ${err.message}`);
    process.exit(1);
});

process.on('SIGTERM', () => {
    console.error('ELK worker received SIGTERM, shutting down');
    process.exit(0);
});

process.on('SIGINT', () => {
    console.error('ELK worker received SIGINT, shutting down');
    process.exit(0);
});

// Start the worker
main().catch(e => {
    console.error(`ELK worker fatal error: ${e.message}`);
    process.exit(1);
});
