import { PRIVILEGED_ROLES, roleForPosition } from './roles';

/*
  Auth service. The UI only talks to the four functions exported at the bottom.

  MOCK MODE (default): runs entirely in the browser so you can demo every role.
  It does NOT verify passwords and is NOT secure. Never ship it.

  REAL MODE: set VITE_API_URL (for example http://localhost:4000/api) in .env.
  The backend must expose the endpoints below and keep the session in an
  httpOnly cookie. The Neon connection string lives ONLY on the server.

    POST /auth/signup  { fullName, email, password, position, role }
                       -> 201 { user }   (user.status is "active" or "pending")
    POST /auth/login   { email, password }
                       -> 200 { user }   |  401/403 { message }
    POST /auth/logout  -> 204
    GET  /auth/me      -> 200 { user }   |  401

  user = { id, email, fullName, position, role, status }
  role = "END_USER" | "SECURITY_AUDITOR" | "CLIENT_ADMIN"

  The server must re-check the role itself. Never trust the role sent by the browser
  (a user could edit it): it should derive the role from the position, and send
  privileged roles to "pending" until an administrator approves them.
*/

const API_URL =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL) || '';

export const isMock = !API_URL;

// Mock-mode switch: Auditor and Admin signups wait for approval before they can log in.
export const REQUIRE_APPROVAL_FOR_PRIVILEGED = true;

export class AuthError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'AuthError';
    this.status = status;
  }
}

/* ---------------------------- real mode ---------------------------- */

async function request(path, { method = 'GET', body } = {}) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new AuthError('Cannot reach the server. Check your connection and try again.');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new AuthError(data.message || 'Something went wrong. Please try again.', res.status);
  }
  return data;
}

/* ----------------------------- mock mode ---------------------------- */

const USERS_KEY = 'aegis.mockUsers';
const SESSION_KEY = 'aegis.session';
const DEMO_PASSWORD = 'demo-pass-123';

export const DEMO_ACCOUNTS = [
  { label: 'End User', email: 'end.user@demo.com', password: DEMO_PASSWORD },
  { label: 'Security Auditor', email: 'auditor@demo.com', password: DEMO_PASSWORD },
  { label: 'Client Admin', email: 'admin@demo.com', password: DEMO_PASSWORD },
];

const SEED_USERS = [
  { id: 'u-1', email: 'end.user@demo.com', fullName: 'Demo End User', position: 'Customer Support Agent', role: 'END_USER', status: 'active' },
  { id: 'u-2', email: 'auditor@demo.com', fullName: 'Demo Auditor', position: 'Information Security Analyst', role: 'SECURITY_AUDITOR', status: 'active' },
  { id: 'u-3', email: 'admin@demo.com', fullName: 'Demo Admin', position: 'IT Manager / Administrator', role: 'CLIENT_ADMIN', status: 'active' },
];

const store = {
  get(key) {
    try {
      const raw = window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage can be blocked; the demo then keeps nothing between reloads */
    }
  },
  remove(key) {
    try {
      window.localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  },
};

const wait = (ms = 600) => new Promise((resolve) => setTimeout(resolve, ms));
const normalize = (email) => email.trim().toLowerCase();
const allUsers = () => [...SEED_USERS, ...(store.get(USERS_KEY) ?? [])];

/* ------------------------------ public API ------------------------------ */

export async function signup({ fullName, email, password, position }) {
  const role = roleForPosition(position);
  if (!role) throw new AuthError('Please choose your position.');

  if (isMock) {
    await wait();
    if (password.length < 8) throw new AuthError('Password must be at least 8 characters.');
    if (allUsers().some((u) => u.email === normalize(email))) {
      throw new AuthError('An account with this email already exists.', 409);
    }
    const needsApproval = REQUIRE_APPROVAL_FOR_PRIVILEGED && PRIVILEGED_ROLES.includes(role);
    const user = {
      id: `u-${Date.now()}`,
      email: normalize(email),
      fullName: fullName.trim(),
      position,
      role,
      status: needsApproval ? 'pending' : 'active',
    };
    store.set(USERS_KEY, [...(store.get(USERS_KEY) ?? []), user]);
    if (user.status === 'active') store.set(SESSION_KEY, user);
    return { user };
  }

  return request('/auth/signup', { method: 'POST', body: { fullName, email, password, position, role } });
}

export async function login(email, password) {
  if (isMock) {
    await wait(500);
    const user = allUsers().find((u) => u.email === normalize(email));
    // Mock only: a real server compares the password hash.
    if (!user || password.length < 8) throw new AuthError('Incorrect email or password.', 401);
    if (user.status === 'pending') {
      throw new AuthError('Your account is waiting for approval by an administrator.', 403);
    }
    store.set(SESSION_KEY, user);
    return { user };
  }

  return request('/auth/login', { method: 'POST', body: { email, password } });
}

export async function logout() {
  if (isMock) {
    store.remove(SESSION_KEY);
    return;
  }
  await request('/auth/logout', { method: 'POST' }).catch(() => {});
}

export async function getSession() {
  if (isMock) return store.get(SESSION_KEY);
  try {
    const { user } = await request('/auth/me');
    return user ?? null;
  } catch {
    return null;
  }
}
