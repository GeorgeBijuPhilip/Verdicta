import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import PropTypes from 'prop-types';
import { useNavigate } from "react-router-dom";

const LandingPage = () => {
  const [particles, setParticles] = useState([]);
  const colors = ["#5A769D"];
  const navigate = useNavigate();
  const secondPageRef = useRef(null);

  useEffect(() => {
    const generateParticles = () => {
      const windowWidth = window.innerWidth;
      const windowHeight = window.innerHeight;

      const newParticles = Array.from({ length: 4 }, (_, i) => ({
        id: i,
        size: Math.random() * 400 + 400,
        color: colors[Math.floor(Math.random() * colors.length)],
        x: Math.random() * windowWidth,
        y: Math.random() * (windowHeight * 2),
        directionX: Math.random() > 0.5 ? 1 : -1,
        directionY: Math.random() > 0.5 ? 1 : -1,
        speedX: 0.8 + Math.random() * 0.5,
        speedY: 0.8 + Math.random() * 0.5,
      }));

      setParticles(newParticles);
    };

    generateParticles();
    window.addEventListener("resize", generateParticles);
    return () => window.removeEventListener("resize", generateParticles);
  }, []);

  const scrollToSecondPage = () => {
    if (secondPageRef.current) {
      secondPageRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="h-screen w-screen overflow-y-auto relative scrollbar-hide">
      {/* Background Layer */}
      <div className="fixed inset-0 bg-black -z-30"></div>

      {/* Particles */}
      <div className="fixed inset-0 -z-10 h-auto">
        {particles.map((particle) => (
          <ParticleElement key={particle.id} particle={particle} />
        ))}
      </div>

      {/* First Page (Hero Section) */}
      <div className="relative h-screen w-full overflow-hidden">
        {/* Navigation Bar */}
        <nav className="absolute top-10 left-10 flex items-center space-x-8">
          <h1 className="text-white text-[40px] font-[Italiana] tracking-wide">
            Verdicta
          </h1>
        </nav>

        {/* Navigation Buttons */}
        <nav className="absolute top-12 right-15 flex space-x-8 items-center">
          <button
            className="text-white text-[25px] font-[Italiana] bg-transparent cursor-pointer hover:text-gray-300 transition-colors duration-300 border-b border-transparent hover:border-white"
            onClick={scrollToSecondPage}
          >
            About Us
          </button>
        </nav>

        {/* Hero Section Content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center space-y-6">
          <motion.h1
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.5 }}
            className="text-white text-[80px] font-[Italiana] tracking-wide"
            style={{ textShadow: "0 0 20px rgba(70, 91, 124, 0.7)" }}
          >
            Your AI Legal Assistant
          </motion.h1>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="relative text-white text-[35px] font-[Italiana] px-1 py-6 border border-white rounded-full bg-transparent backdrop-blur-lg shadow-lg"
            style={{
              width: "220px",
              height: "84px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 4px 30px rgba(255, 255, 255, 0.25)",
              borderRadius: "50px",
            }}
            onClick={() => { navigate("/login") }}
          >
            Chat
          </motion.button>
        </div>
      </div>

      {/* Second Page */}
      <div ref={secondPageRef} className="min-h-screen w-full flex flex-col items-center justify-center px-8 py-16">
        <div className="backdrop-blur-sm bg-black/30 p-12 rounded-2xl max-w-6xl">
          <h2 className="text-white text-6xl font-[Italiana] mb-12 text-center">Why Verdicta</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-black/30 p-8 rounded-lg backdrop-blur-lg border border-white/20">
              <h3 className="text-white text-2xl font-[Italiana] mb-4">Expert Legal Analysis</h3>
              <p className="text-gray-300">
                Our AI is trained on thousands of legal documents and precedents to provide accurate and reliable legal assistance.
              </p>
            </div>
            <div className="bg-black/30 p-8 rounded-lg backdrop-blur-lg border border-white/20">
              <h3 className="text-white text-2xl font-[Italiana] mb-4">24/7 Availability</h3>
              <p className="text-gray-300">
                Get legal assistance whenever you need it, day or night, without scheduling appointments or waiting for callbacks.
              </p>
            </div>
            <div className="bg-black/30 p-8 rounded-lg backdrop-blur-lg border border-white/20">
              <h3 className="text-white text-2xl font-[Italiana] mb-4">Cost Effective</h3>
              <p className="text-gray-300">
                Access legal advice at a fraction of the cost of traditional legal services, making justice more accessible to everyone.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const ParticleElement = ({ particle }) => {
  const [position, setPosition] = useState({
    x: particle.x - particle.size / 2,
    y: particle.y - particle.size / 2,
    directionX: particle.directionX,
    directionY: particle.directionY,
  });

  useEffect(() => {
    let animationFrameId;

    const moveParticle = () => {
      setPosition((prevPos) => {
        let newX = prevPos.x + prevPos.directionX * particle.speedX;
        let newY = prevPos.y + prevPos.directionY * particle.speedY;
        let newDirX = prevPos.directionX;
        let newDirY = prevPos.directionY;

        if (newX <= 0 || newX >= window.innerWidth - particle.size) newDirX *= -1;
        if (newY <= 0 || newY >= window.innerHeight * 2 - particle.size) newDirY *= -1;

        return { x: newX, y: newY, directionX: newDirX, directionY: newDirY };
      });
      animationFrameId = requestAnimationFrame(moveParticle);
    };

    animationFrameId = requestAnimationFrame(moveParticle);
    return () => cancelAnimationFrame(animationFrameId);
  }, [particle]);

  return (
    <motion.div
      className="absolute rounded-full"
      style={{
        width: particle.size,
        height: particle.size,
        backgroundColor: particle.color,
        filter: "blur(30px)",
        opacity: 1,
        left: position.x,
        top: position.y,
        mixBlendMode: "screen",
      }}
      animate={{ x: position.x, y: position.y }}
      transition={{ ease: "easeInOut", duration: 4, repeat: Infinity }}
    />
  );
};

// PropTypes validation
ParticleElement.propTypes = {
  particle: PropTypes.shape({
    id: PropTypes.number.isRequired,
    size: PropTypes.number.isRequired,
    color: PropTypes.string.isRequired,
    x: PropTypes.number.isRequired,
    y: PropTypes.number.isRequired,
    directionX: PropTypes.number.isRequired,
    directionY: PropTypes.number.isRequired,
    speedX: PropTypes.number.isRequired,
    speedY: PropTypes.number.isRequired,
  }).isRequired
};

export default LandingPage;