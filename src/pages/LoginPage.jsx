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
    <div className="relative flex items-center justify-center min-h-screen w-screen bg-cover bg-center" style={{ backgroundImage: "url('/assets/bg.png')", fontFamily: 'Italiana, serif' }}>
      {/* Verdicta Text */}
      <h1 className="absolute top-5 left-5 text-white text-3xl">Verdicta</h1>

      {/* Login Box */}
      <div className="w-full max-w-md p-8 bg-transparent border-none shadow-none bg-opacity-70 backdrop-blur-md rounded-lg shadow-lg text-white flex flex-col justify-center">
        <h2 className="text-center text-3xl text-white mb-5" style={{ fontFamily: 'Italiana, serif' }}>Login</h2>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Email:</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 text-black py-2 rounded-md bg-white border border-gray-600 focus:border-blue-500 focus:ring focus:ring-blue-300 outline-none placeholder-gray-400"
              placeholder="Enter your email"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Password:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 text-black py-2 rounded-md bg-white border border-gray-600 focus:border-blue-500 focus:ring focus:ring-blue-300 outline-none placeholder-gray-400"
              placeholder="Enter your password"
            />
          </div>

          {error && <p className="text-center text-red-400 bg-gray-800 py-2 rounded-md">{error}</p>}

          {/* Centering the button */}
          <div className="flex justify-center">
            <button
              type="submit"
              className="w-[120px] py-2 bg-white transition-all text-black rounded-md shadow-md"
              style={{ fontFamily: 'Italiana, serif' }}
            >
              Login
            </button>
          </div>
        </form>

        <p className="text-center text-sm mt-4">
          Don&apos;t have an account?{" "}
          <a href="/signup" className="text-blue-400 hover:underline">
            Sign Up
          </a>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;