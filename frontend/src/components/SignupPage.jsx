import React, { useState } from 'react';
import { ArrowLeft, Check, Eye, EyeOff, Loader2, MailCheck } from 'lucide-react';
import AuthLayout from './AuthLayout';
import { useAuth } from './AuthContext';
import { REQUIRE_APPROVAL_FOR_PRIVILEGED } from './authApi';
import { PRIVILEGED_ROLES, ROLE_GROUPS, groupForRole, roleForPosition } from './roles';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Strength is shown with a word as well as color, so it does not rely on color alone.
const STRENGTH_LEVELS = [
  { label: '', bar: 'bg-line', text: 'text-ink-muted' },
  { label: 'Weak', bar: 'bg-danger', text: 'text-danger' },
  { label: 'Fair', bar: 'bg-warning', text: 'text-warning' },
  { label: 'Good', bar: 'bg-success', text: 'text-success' },
  { label: 'Strong', bar: 'bg-success', text: 'text-success' },
];

function passwordStrength(pw) {
  if (!pw) return { level: 0, ...STRENGTH_LEVELS[0] };
  let points = 0;
  if (pw.length >= 8) points += 1;
  if (pw.length >= 12) points += 1;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) points += 1;
  if (/\d/.test(pw)) points += 1;
  if (/[^A-Za-z0-9]/.test(pw)) points += 1;
  // Anything under 8 characters is always Weak
  const level = pw.length < 8 ? 1 : Math.min(4, Math.max(2, points - 1));
  return { level, ...STRENGTH_LEVELS[level] };
}

function Field({ id, label, error, hint, children }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-ink">{label}</label>
      <div className="mt-1.5">{children}</div>
      {hint && !error && <p className="mt-1.5 text-xs text-ink-muted">{hint}</p>}
      {error && <p id={`${id}-error`} className="mt-1.5 text-sm text-danger">{error}</p>}
    </div>
  );
}

const inputClass = (hasError) =>
  `w-full rounded-lg border bg-surface px-3 py-2.5 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-1 focus:ring-brand ${
    hasError ? 'border-danger' : 'border-line-strong focus:border-brand'
  }`;

export default function SignupPage() {
  const { signup } = useAuth();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ fullName: '', email: '', password: '', confirm: '' });
  const [position, setPosition] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);
  const [pendingUser, setPendingUser] = useState(null);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const strength = passwordStrength(form.password);

  const role = roleForPosition(position);
  const group = role ? groupForRole(role) : null;
  const needsApproval = REQUIRE_APPROVAL_FOR_PRIVILEGED && role && PRIVILEGED_ROLES.includes(role);

  const validateStep1 = () => {
    const next = {};
    if (!form.fullName.trim()) next.fullName = 'Enter your full name.';
    if (!form.email.trim()) next.email = 'Enter your work email.';
    else if (!EMAIL_RE.test(form.email.trim())) next.email = 'Enter a valid email address.';
    if (form.password.length < 8) next.password = 'Use at least 8 characters.';
    if (form.confirm !== form.password) next.confirm = 'Passwords do not match.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const goToStep2 = (e) => {
    e.preventDefault();
    setFormError('');
    if (validateStep1()) setStep(2);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setFormError('');
    if (!position) {
      setErrors({ position: 'Choose the position that fits you best.' });
      return;
    }
    setErrors({});
    setBusy(true);
    try {
      const user = await signup({
        fullName: form.fullName,
        email: form.email,
        password: form.password,
        position,
      });
      if (user.status === 'pending') setPendingUser(user);
      // Active accounts are signed in by the auth provider and AppRoutes opens the dashboard.
    } catch (err) {
      setFormError(err.message || 'Could not create your account. Please try again.');
      if (err.status === 409) setStep(1);
    } finally {
      setBusy(false);
    }
  };

  /* Account created but waiting for approval */
  if (pendingUser) {
    return (
      <AuthLayout>
        <div className="rounded-xl border border-line bg-surface p-6 text-center">
          <MailCheck className="mx-auto w-10 h-10 text-brand" />
          <h1 className="mt-4 text-xl font-semibold text-ink">Account created</h1>
          <p className="mt-2 text-sm text-ink-muted">
            Thanks, {pendingUser.fullName.split(' ')[0]}. Because of your position, an administrator needs to approve
            your access before you can sign in. We will use <span className="font-medium text-ink">{pendingUser.email}</span> to let you know.
          </p>
          <a
            href="#/login"
            className="mt-6 inline-block rounded-lg bg-brand-strong px-4 py-2.5 text-sm font-semibold text-canvas hover:bg-brand transition-colors"
          >
            Back to sign in
          </a>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout wide>
      <p className="text-xs uppercase tracking-wider font-semibold text-ink-muted" aria-live="polite">
        Step {step} of 2
      </p>
      <div className="mt-2 flex gap-1.5" aria-hidden="true">
        <span className="h-1 flex-1 rounded-full bg-brand" />
        <span className={`h-1 flex-1 rounded-full ${step === 2 ? 'bg-brand' : 'bg-line'}`} />
      </div>

      {formError && (
        <div role="alert" className="mt-6 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {formError}
        </div>
      )}

      {step === 1 && (
        <>
          <h1 className="mt-6 text-2xl font-semibold text-ink">Create your account</h1>
          <p className="mt-1 text-sm text-ink-muted">Start with your details. You will choose your position next.</p>

          <form onSubmit={goToStep2} noValidate className="mt-6 space-y-5">
            <Field id="su-name" label="Full name" error={errors.fullName}>
              <input
                id="su-name"
                autoComplete="name"
                value={form.fullName}
                onChange={set('fullName')}
                aria-invalid={!!errors.fullName}
                aria-describedby={errors.fullName ? 'su-name-error' : undefined}
                className={inputClass(errors.fullName)}
              />
            </Field>

            <Field id="su-email" label="Work email" error={errors.email}>
              <input
                id="su-email"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={set('email')}
                aria-invalid={!!errors.email}
                aria-describedby={errors.email ? 'su-email-error' : undefined}
                placeholder="you@company.com"
                className={inputClass(errors.email)}
              />
            </Field>

            <Field id="su-password" label="Password" error={errors.password} hint="At least 8 characters. A longer phrase with numbers is stronger.">
              <div className="relative">
                <input
                  id="su-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={form.password}
                  onChange={set('password')}
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? 'su-password-error' : undefined}
                  className={`${inputClass(errors.password)} pr-11`}
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
              {form.password && (
                <div className="mt-2 flex items-center gap-3" aria-live="polite">
                  <div className="flex flex-1 gap-1" aria-hidden="true">
                    {[1, 2, 3, 4].map((i) => (
                      <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= strength.level ? strength.bar : 'bg-line'}`} />
                    ))}
                  </div>
                  <span className={`text-xs font-semibold ${strength.text}`}>{strength.label}</span>
                </div>
              )}
            </Field>

            <Field id="su-confirm" label="Confirm password" error={errors.confirm}>
              <input
                id="su-confirm"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={form.confirm}
                onChange={set('confirm')}
                aria-invalid={!!errors.confirm}
                aria-describedby={errors.confirm ? 'su-confirm-error' : undefined}
                className={inputClass(errors.confirm)}
              />
            </Field>

            <button
              type="submit"
              className="w-full rounded-lg bg-brand-strong px-4 py-2.5 text-sm font-semibold text-canvas hover:bg-brand transition-colors"
            >
              Continue
            </button>
          </form>

          <p className="mt-6 text-sm text-ink-muted">
            Already have an account?{' '}
            <a href="#/login" className="font-semibold text-brand hover:underline">Sign in</a>
          </p>
        </>
      )}

      {step === 2 && (
        <form onSubmit={handleCreate} noValidate>
          <h1 className="mt-6 text-2xl font-semibold text-ink">What is your position?</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Pick the job title closest to yours. It decides which parts of the platform you can use.
          </p>

          <fieldset className="mt-6 space-y-6" aria-describedby={errors.position ? 'position-error' : undefined}>
            <legend className="sr-only">Your position</legend>

            {ROLE_GROUPS.map((g) => (
              <div key={g.role}>
                <p className="text-sm font-semibold text-ink">{g.title}</p>
                <p className="text-xs text-ink-muted">{g.description}</p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {g.positions.map((p) => (
                    <label key={p} className="cursor-pointer">
                      <input
                        type="radio"
                        name="position"
                        value={p}
                        checked={position === p}
                        onChange={() => setPosition(p)}
                        className="peer sr-only"
                      />
                      <span className="inline-flex items-center gap-1.5 rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm text-ink transition-colors hover:border-brand peer-checked:border-brand peer-checked:bg-brand/10 peer-checked:font-semibold peer-focus-visible:ring-2 peer-focus-visible:ring-brand">
                        {position === p && <Check className="w-3.5 h-3.5 text-brand" />}
                        {p}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </fieldset>

          {errors.position && <p id="position-error" className="mt-3 text-sm text-danger">{errors.position}</p>}

          {/* Plain-language summary of what the chosen position can do */}
          {group && (
            <div className="mt-6 rounded-lg border border-line bg-raised p-4" aria-live="polite">
              <p className="text-sm font-semibold text-ink">With this position you will be able to:</p>
              <ul className="mt-2 space-y-1.5 text-sm text-ink-muted">
                {group.access.map((line) => (
                  <li key={line} className="flex items-start gap-2">
                    <Check className="w-4 h-4 mt-0.5 shrink-0 text-success" />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
              {needsApproval && (
                <p className="mt-3 text-xs text-ink-muted border-t border-line pt-3">
                  Accounts with this access are reviewed by an administrator before they are activated.
                </p>
              )}
            </div>
          )}

          <div className="mt-8 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => { setStep(1); setFormError(''); }}
              className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-ink"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-brand-strong px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-brand disabled:bg-raised disabled:text-ink-muted transition-colors flex items-center gap-2"
            >
              {busy ? (<><Loader2 className="w-4 h-4 animate-spin" /> Creating account...</>) : 'Create account'}
            </button>
          </div>
        </form>
      )}
    </AuthLayout>
  );
}
