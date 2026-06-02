import { useState } from 'react';
import { supabase } from '../supabaseClient';
import mySetuLogo from '../assets/mysetu_logo.png';
import './Auth.css';

export default function Auth() {
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLogin, setIsLogin] = useState(true);
  const [message, setMessage] = useState('');

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      if (isLogin) {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      } else {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setMessage('Check your email for the login link!');
      }
    } catch (error) {
      setMessage(error.error_description || error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Logo */}
        <div className="auth-logo">
          <img src={mySetuLogo} alt="mySetu" />
          <span className="auth-logo-name">
            my<span className="blue">Setu</span> <span className="green">AI</span>
          </span>
          <span className="auth-tagline">Be cause we care</span>
        </div>

        <h2 className="auth-title">{isLogin ? 'Welcome back' : 'Create Account'}</h2>
        <p className="auth-subtitle">
          {isLogin ? 'Sign in to your organizational intelligence platform' : 'Join mySetu AI — your knowledge assistant'}
        </p>

        {message && <div className="auth-error">{message}</div>}

        <form onSubmit={handleAuth} className="auth-form">
          <input
            className="auth-input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email address"
            required
          />
          <input
            className="auth-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
          />
          <button className="auth-btn" type="submit" disabled={loading}>
            {loading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Create Account')}
          </button>
        </form>

        <p className="auth-switch">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button type="button" onClick={() => setIsLogin(!isLogin)}>
            {isLogin ? 'Register' : 'Sign In'}
          </button>
        </p>
      </div>
    </div>
  );
}
