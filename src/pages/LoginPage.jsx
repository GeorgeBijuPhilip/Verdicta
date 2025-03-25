import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();

    // Retrieve stored users from localStorage
    const users = JSON.parse(localStorage.getItem('users')) || [];
    const user = users.find(user => user.email === email && user.password === password);

    if (user) {
      navigate('/chat'); // Redirect to the Chat component
    } else {
      setError('Invalid email or password');
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.loginBox}>
        <h2 style={styles.title}>Login</h2>
        <form onSubmit={handleLogin} style={styles.form}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Email:</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={styles.input}
              placeholder="Enter your email"
            />
          </div>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Password:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={styles.input}
              placeholder="Enter your password"
            />
          </div>
          {error && <p style={styles.error}>{error}</p>}
          <button type="submit" style={styles.button}>
            Login
          </button>
        </form>
        <p style={styles.redirectText}>
          Don&apos;t have an account? <a href="/signup" style={styles.link}>Sign Up</a>
        </p>
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
    padding: '20px',
    boxSizing: 'border-box',
  },
  loginBox: {
    width: '100%',
    maxWidth: '400px',
    padding: '30px',
    backgroundColor: '#1e1e1e',
    borderRadius: '16px',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    boxSizing: 'border-box',
  },
  title: {
    textAlign: 'center',
    marginBottom: '20px',
    color: '#42a5f5',
  },
  form: {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  inputGroup: {
    width: '100%',
    marginBottom: '15px',
  },
  label: {
    marginBottom: '5px',
    fontSize: '14px',
    color: '#e0e0e0',
  },
  input: {
    width: '100%',
    padding: '12px',
    borderRadius: '8px',
    border: '1px solid #333',
    backgroundColor: '#2c2c2c',
    color: '#e0e0e0',
    outline: 'none',
    transition: 'border-color 0.3s ease',
    boxSizing: 'border-box',
  },
  button: {
    width: '100%',
    padding: '12px',
    backgroundColor: '#ff4444',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background-color 0.3s ease',
    marginTop: '10px',
  },
  error: {
    width: '100%',
    color: '#ff4444',
    backgroundColor: '#2c2c2c',
    padding: '10px',
    borderRadius: '8px',
    marginBottom: '15px',
    border: '1px solid #ff4444',
    textAlign: 'center',
    boxSizing: 'border-box',
  },
  redirectText: {
    marginTop: '10px',
    fontSize: '14px',
    color: '#e0e0e0',
  },
  link: {
    color: '#42a5f5',
    textDecoration: 'none',
  },
};

export default LoginPage;
