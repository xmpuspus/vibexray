/**
 * index.ts — Express application entry point.
 *
 * Mounts all route groups and starts the HTTP server.
 */

import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import authRoutes from './routes/auth';
import ordersRoutes from './routes/orders';
import menuRoutes from './routes/menu';
import chatRoutes from './routes/chat';

const app = express();
const PORT = process.env.PORT ?? 3001;

// ── Middleware ────────────────────────────────────────────────────────────────

app.use(
  cors({
    origin: process.env.CORS_ORIGIN ?? 'http://localhost:5173',
    credentials: true,
  }),
);

app.use(express.json({ limit: '1mb' }));

// ── Routes ────────────────────────────────────────────────────────────────────

app.use('/api/auth', authRoutes);
app.use('/api/orders', ordersRoutes);
app.use('/api/menu', menuRoutes);
app.use('/api/chat', chatRoutes);

// Health check
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 404 fallback
app.use((_req, res) => {
  res.status(404).json({ error: 'NOT_FOUND', code: '404', message: 'Route not found.' });
});

// ── Start ─────────────────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`\nSliceIQ backend running on http://localhost:${PORT}`);
  console.log(`Health: http://localhost:${PORT}/health\n`);
});

export default app;
