import React, { useState } from 'react';
import { supabase } from './supabaseClient';

const AuthPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSignUp = async () => {
    setLoading(true);
    setError(null);
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) setError(error.message);
    else setError('Check your email for a confirmation link!');
    setLoading(false);
  };

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) setError(error.message);
    else setAccessToken(data.session?.access_token || null);
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 400, margin: '2rem auto', padding: 24, border: '1px solid #eee', borderRadius: 8 }}>
      <h2>Sign Up / Log In</h2>
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={e => setEmail(e.target.value)}
        style={{ width: '100%', marginBottom: 8, padding: 8 }}
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={e => setPassword(e.target.value)}
        style={{ width: '100%', marginBottom: 8, padding: 8 }}
      />
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <button onClick={handleSignUp} disabled={loading} style={{ flex: 1 }}>Sign Up</button>
        <button onClick={handleLogin} disabled={loading} style={{ flex: 1 }}>Log In</button>
      </div>
      {error && <div style={{ color: 'red', marginBottom: 8 }}>{error}</div>}
      {accessToken && (
        <div style={{ wordBreak: 'break-all', background: '#f6f6f6', padding: 8, borderRadius: 4 }}>
          <strong>Access Token:</strong>
          <div style={{ fontSize: 12 }}>{accessToken}</div>
        </div>
      )}
    </div>
  );
};

export default AuthPage; 