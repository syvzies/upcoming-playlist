// Simple CORS proxy server using Node.js
// Save this as cors-proxy.js and run with: node cors-proxy.js

const http = require('http');
const https = require('https');
const url = require('url');

const PORT = process.env.PORT || 8081;

const server = http.createServer((req, res) => {
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');

    // Handle preflight requests
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // Only allow GET requests
    if (req.method !== 'GET') {
        res.writeHead(405, {'Content-Type': 'text/plain'});
        res.end('Method Not Allowed');
        return;
    }

    // Get the target URL from the query parameter
    const parsedUrl = url.parse(req.url, true);
    const targetUrl = parsedUrl.query.url;

    if (!targetUrl) {
        res.writeHead(400, {'Content-Type': 'text/plain'});
        res.end('Missing URL parameter');
        return;
    }

    console.log(`Proxying request to: ${targetUrl}`);

    // Determine the protocol (http or https)
    const parsedTargetUrl = url.parse(targetUrl);
    const httpModule = parsedTargetUrl.protocol === 'https:' ? https : http;

    // Forward the request
    const proxyReq = httpModule.request(targetUrl, (proxyRes) => {
        // Copy response headers
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        
        // Pipe the response data
        proxyRes.pipe(res, { end: true });
    });

    // Handle request errors
    proxyReq.on('error', (err) => {
        console.error(`Error proxying request: ${err.message}`);
        res.writeHead(500, {'Content-Type': 'text/plain'});
        res.end(`Proxy Error: ${err.message}`);
    });

    // End the request
    proxyReq.end();
});

server.listen(PORT, () => {
    console.log(`CORS Proxy running on port ${PORT}`);
    console.log(`Usage: http://localhost:${PORT}/?url=https://example.com`);
});