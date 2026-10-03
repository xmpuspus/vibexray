/**
 * routes/auth.ts — POST /api/auth/register and POST /api/auth/login
 *
 * Passwords are hashed with bcrypt (cost 10). JWT tokens are signed with
 * JWT_SECRET and expire in 7 days.
 */

import { Router, Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { ApiError } from '../types';

const router = Router();
const prisma = new PrismaClient();

// ── POST /api/auth/register ──────────────────────────────────────────────────

router.post('/register', async (req: Request, res: Response) => {
  const { email, name, password } = req.body as {
    email?: string;
    name?: string;
    password?: string;
  };

  if (!email || !name || !password) {
    const err: ApiError = {
      error: 'VALIDATION_ERROR',
      code: '400',
      message: 'email, name, and password are required.',
    };
    return res.status(400).json(err);
  }

  if (password.length < 6) {
    const err: ApiError = {
      error: 'VALIDATION_ERROR',
      code: '400',
      message: 'Password must be at least 6 characters.',
    };
    return res.status(400).json(err);
  }

  try {
    const existing = await prisma.customer.findUnique({ where: { email } });
    if (existing) {
      const err: ApiError = {
        error: 'CONFLICT',
        code: '409',
        message: `An account with email "${email}" already exists.`,
      };
      return res.status(409).json(err);
    }

    const passwordHash = await bcrypt.hash(password, 10);
    const customer = await prisma.customer.create({
      data: { email, name, passwordHash },
    });

    const token = signToken(customer.id, customer.email);
    return res.status(201).json({
      token,
      customer: { id: customer.id, email: customer.email, name: customer.name },
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    const apiErr: ApiError = { error: 'SERVER_ERROR', code: '500', message: msg };
    return res.status(500).json(apiErr);
  }
});

// ── POST /api/auth/login ─────────────────────────────────────────────────────

router.post('/login', async (req: Request, res: Response) => {
  const { email, password } = req.body as { email?: string; password?: string };

  if (!email || !password) {
    const err: ApiError = {
      error: 'VALIDATION_ERROR',
      code: '400',
      message: 'email and password are required.',
    };
    return res.status(400).json(err);
  }

  try {
    const customer = await prisma.customer.findUnique({ where: { email } });

    // Use constant-time comparison to avoid timing attacks
    const dummyHash = '$2a$10$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';
    const hashToCheck = customer?.passwordHash ?? dummyHash;
    const passwordMatch = await bcrypt.compare(password, hashToCheck);

    if (!customer || !passwordMatch) {
      const err: ApiError = {
        error: 'UNAUTHORIZED',
        code: '401',
        message: 'Invalid email or password.',
      };
      return res.status(401).json(err);
    }

    const token = signToken(customer.id, customer.email);
    return res.json({
      token,
      customer: { id: customer.id, email: customer.email, name: customer.name },
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    const apiErr: ApiError = { error: 'SERVER_ERROR', code: '500', message: msg };
    return res.status(500).json(apiErr);
  }
});

// ── Helper ───────────────────────────────────────────────────────────────────

function signToken(customerId: string, email: string): string {
  const secret = process.env.JWT_SECRET;
  if (!secret) throw new Error('JWT_SECRET not configured');
  return jwt.sign({ customerId, email }, secret, { expiresIn: '7d' });
}

export default router;
