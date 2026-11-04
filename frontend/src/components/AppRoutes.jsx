import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { AuthProvider, useAuth } from './AuthContext';
import { homeFor } from './roles';
import LoginPage from './LoginPage';
import SignupPage from './SignupPage';
import Dashboard from './Dashboard';

const readHash = () => window.location.hash.replace(/^#\/?/, '');

function useHash() {
  const [hash, setHash] = useState(readHash);
  useEffect(() => {
    const onChange = () => setHash(readHash());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return hash;
}

// Decides what to show: login, signup, or the dashboard.
// What is rendered never depends on the redirect below, which only keeps the address bar honest.
function Gate() {
  const { user, loading } = useAuth();
  const page = useHash();

  const isAuthPage = page === 'login' || page === 'signup';
  const target = user ? (isAuthPage ? `/${homeFor(user.role)}` : null) : isAuthPage ? null : '/login';

  useEffect(() => {
    if (!loading && target) window.location.hash = target;
  }, [loading, target]);

  if (loading) {
    return (
      <div role="status" aria-label="Loading" className="min-h-screen flex items-center justify-center bg-canvas">
        <Loader2 className="w-6 h-6 animate-spin text-brand" />
      </div>
    );
  }

  if (!user) return page === 'signup' ? <SignupPage /> : <LoginPage />;
  return <Dashboard />;
}

export default function AppRoutes() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  );
}
