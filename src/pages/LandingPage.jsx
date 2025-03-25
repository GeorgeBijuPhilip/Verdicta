import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import PropTypes from 'prop-types';
import { useNavigate } from "react-router-dom";

const LandingPage = () => {
  const [particles, setParticles] = useState([]);
  const colors = ["#5A769D"];
  const navigate = useNavigate();

  useEffect(() => {
    const generateParticles = () => {
      const windowWidth = window.innerWidth;
      const windowHeight = window.innerHeight;

      const newParticles = Array.from({ length: 3}, (_, i) => ({
        id: i,
        size: Math.random() * 400 + 400,
        color: colors[Math.floor(Math.random() * colors.length)],
        x: Math.random() * windowWidth,
        y: Math.random() * windowHeight,
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fixed inset-0 overflow-hidden bg-black">
      {/* Background Image Layer */}
      <div className="absolute inset-0 -z-20">
        <div
          className="w-full h-full opacity-0 transition-opacity duration-500"
          style={{
            backgroundImage: "url('/mnt/data/Desktop - 1.png')",
            backgroundSize: "cover",
            backgroundPosition: "center",
            mixBlendMode: "screen",
          }}
        ></div>
      </div>

      {/* Particle Background */}
      <div className="absolute inset-0 -z-10">
        {particles.map((particle) => (
          <ParticleElement key={particle.id} particle={particle} />
        ))}
      </div>

      {/* Navigation Bar */}
      <nav className="absolute top-6 left-6 flex items-center space-x-8">
        <h1 className="text-white text-[45px] font-[Italiana] tracking-wide">
          Verdicta
        </h1>
      </nav>
      <nav className="absolute top-6 right-8 flex space-x-8">
        <a className="text-white text-[34px] font-[Italiana]">Home</a>
        <a className="text-white text-[34px] font-[Italiana]">About Us</a>
        <a className="text-white text-[34px] font-[Italiana]">Contact</a>
      </nav>

      <div className="absolute inset-0 flex flex-col items-center justify-center space-y-6">
        <motion.h1
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.5 }}
          className="text-white text-[90px] font-[Italiana] tracking-wide"
          style={{ textShadow: "0 0 20px rgba(70, 91, 124, 0.7)" }}
        >
          Your AI Legal Assistant
        </motion.h1>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="relative text-white text-[41px] font-[Italiana] px-12 py-6 border border-white rounded-full bg-transparent backdrop-blur-lg shadow-lg"
          style={{
            width: "240px",
            height: "92px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 30px rgba(255, 255, 255, 0.25)",
            borderRadius: "50px",
          }}
          onClick={() => {navigate("/login")}}
        >
          Chat
        </motion.button>
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
        if (newY <= 0 || newY >= window.innerHeight - particle.size) newDirY *= -1;

        return {
          x: newX,
          y: newY,
          directionX: newDirX,
          directionY: newDirY,
        };
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