import { useState } from "react";
import { useNavigate } from "react-router-dom";

const SignupPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSignup = (e) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    // Store user details in localStorage (simulating a database)
    const users = JSON.parse(localStorage.getItem("users")) || [];

    if (users.some((user) => user.email === email)) {
      setError("Email already exists. Try logging in.");
      return;
    }

    users.push({ email, password });
    localStorage.setItem("users", JSON.stringify(users));

    alert("Signup successful! You can now log in.");
    navigate("/login"); // Redirect to login page
  };

  return (
    <div className="relative flex items-center justify-center min-h-screen w-screen bg-cover bg-center" style={{ backgroundImage: "url('/assets/bg.png')", fontFamily: 'Italiana, serif' }}>
      {/* Verdicta Text */}
      <h1 className="absolute top-5 left-5 text-white text-3xl">Verdicta</h1>

      {/* Signup Box */}
      <div className="w-full max-w-md p-8 bg-transparent border-none shadow-none bg-opacity-70 backdrop-blur-md rounded-lg shadow-lg text-white flex flex-col justify-center">
      <h2 className="text-center text-3xl text-white mb-5" style={{ fontFamily: 'Italiana, serif' }}>Sign Up</h2>

      <form onSubmit={handleSignup} className="space-y-4">
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
            placeholder="Create a password"
          />
        </div>
        <div>
          <label className="block text-sm mb-1">Confirm Password:</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            className="w-full px-4 text-black py-2 rounded-md bg-white border border-gray-600 focus:border-blue-500 focus:ring focus:ring-blue-300 outline-none placeholder-gray-400"
            placeholder="Confirm your password"
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
            Sign Up
          </button>
        </div>
      </form>

      <p className="text-center text-sm mt-4">
        Already have an account?{" "}
        <a href="/login" className="text-blue-400 hover:underline">
          Login
        </a>
      </p>
    </div>

    </div>
  );
};

export default SignupPage;
