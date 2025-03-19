import React from 'react';
import { useNavigate } from 'react-router-dom';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div style={styles.container}>
      <div style={styles.content}>
        <h1 style={styles.title}>AI Legal Assistant</h1>
        <p style={styles.description}>
        Empowering Your Legal Journey with AI.
        </p>
        <button onClick={() => navigate('/signup')} style={styles.button}>
          Get Started
        </button>
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#121212',
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif',
    color: '#e0e0e0',
    textAlign: 'center',
    padding: '20px',
    boxSizing: 'border-box',
  },
  content: {
    maxWidth: '600px',
    padding: '30px',
    backgroundColor: '#1e1e1e',
    borderRadius: '16px',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
  },
  title: {
    fontSize: '32px',
    marginBottom: '20px',
    color: '#42a5f5',
  },
  description: {
    fontSize: '18px',
    marginBottom: '20px',
  },
  button: {
    padding: '12px 24px',
    backgroundColor: '#ff4444',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background-color 0.3s ease',
    fontSize: '16px',
  },
};

export default LandingPage;
