import React, { useState } from 'react';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import AuthLayout from './AuthLayout';
import { useAuth } from './AuthContext';
import { DEMO_ACCOUNTS, isMock } from './authApi';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);

  const validate = () => {
    const next = {};
    if (!email.trim()) next.email = 'Enter your work email.';
    else if (!EMAIL_RE.test(email.trim())) next.email = 'Enter a valid email address.';
    if (!password) next.password = 'Enter your password.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    if (!validate()) return;
    setBusy(true);
    try {
      await login(email, password);
      // AppRoutes sees the new user and opens the dashboard.
    } catch (err) {
      setFormError(err.message || 'Could not sign in. Please try again.');
      setBusy(false);
    }
  };

  const fillDemo = (account) => {
    setEmail(account.email);
    setPassword(account.password);
    setErrors({});
    setFormError('');
  };

  return (
    <AuthLayout>
      <h1 className="text-2xl font-semibold text-ink">Sign in</h1>
      <p className="mt-1 text-sm text-ink-muted">Welcome back. Use your work email to continue.</p>

      {formError && (
        <div role="alert" className="mt-6 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {formError}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-5">
        <div>
          <label htmlFor="login-email" className="block text-sm font-medium text-ink">Work email</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'login-email-error' : undefined}
            className={`mt-1.5 w-full rounded-lg border bg-surface px-3 py-2.5 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-1 focus:ring-brand ${
              errors.email ? 'border-danger' : 'border-line-strong focus:border-brand'
            }`}
            placeholder="you@company.com"
          />
          {errors.email && <p id="login-email-error" className="mt-1.5 text-sm text-danger">{errors.email}</p>}
        </div>

        <div>
          <label htmlFor="login-password" className="block text-sm font-medium text-ink">Password</label>
          <div className="relative mt-1.5">
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? 'login-password-error' : undefined}
              className={`w-full rounded-lg border bg-surface py-2.5 pl-3 pr-11 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-1 focus:ring-brand ${
                errors.password ? 'border-danger' : 'border-line-strong focus:border-brand'
              }`}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="absolute inset-y-0 right-0 flex items-center px-3 text-ink-muted hover:text-ink"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {errors.password && <p id="login-password-error" className="mt-1.5 text-sm text-danger">{errors.password}</p>}
        </div>

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-brand-strong px-4 py-2.5 text-sm font-semibold text-canvas hover:bg-brand disabled:bg-raised disabled:text-ink-muted transition-colors flex items-center justify-center gap-2"
        >
          {busy ? (<><Loader2 className="w-4 h-4 animate-spin" /> Signing in...</>) : 'Sign in'}
        </button>
      </form>

      <p className="mt-6 text-sm text-ink-muted">
        New to AegisAI?{' '}
        <a href="#/signup" className="font-semibold text-brand hover:underline">Create an account</a>
      </p>

      {/* Mock mode only: quick sign-in so every role can be demonstrated */}
      {isMock && (
        <div className="mt-8 rounded-lg border border-line bg-raised p-4">
          <p className="text-xs uppercase tracking-wider font-semibold text-ink-muted">Demo accounts</p>
          <p className="mt-1 text-xs text-ink-muted">Fills the form for you. Visible only while the app runs without a backend.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                onClick={() => fillDemo(account)}
                className="rounded-md border border-line-strong bg-surface px-3 py-1.5 text-xs font-medium text-ink hover:border-brand transition-colors"
              >
                {account.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </AuthLayout>
  );
}
