import { useState, useCallback, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min?url";
import { useNavigate } from "react-router-dom";
import "./Chatbotstyles.css";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  // eslint-disable-next-line no-unused-vars
  const [files, setFiles] = useState([]);
  const [filePreview, setFilePreview] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const navigate = useNavigate();

  // Check if the user is logged in
  useEffect(() => {
    const user = JSON.parse(localStorage.getItem("users")) || [];
    const loggedInUser = user.find((u) => u.email); // Assuming the first user is the logged-in user
    
    if (!loggedInUser) {
      // Redirect to signup if no valid user is found in localStorage
      navigate("/signup");
    }
  }, [navigate]);

  // Scroll to the bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const extractTextFromImage = (imageFile) => {
    return new Promise((resolve, reject) => {
      const worker = new Worker(new URL("./tesseractWorker.js", import.meta.url), { type: "module" });
      worker.postMessage(imageFile);
      worker.onmessage = (event) => {
        if (event.data.error) reject(new Error(event.data.error));
        else resolve(event.data.text);
        worker.terminate();
      };
      worker.onerror = (error) => {
        reject(new Error(error.message || "Image processing failed"));
        worker.terminate();
      };
    });
  };

  const extractTextFromPDF = async (pdfFile) => {
    try {
      const arrayBuffer = await pdfFile.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      let extractedText = "";
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        extractedText += textContent.items.map((item) => item.str).join(" ");
      }
      return extractedText.trim();
    } catch (error) {
      console.error("PDF extraction error:", error);
      throw new Error("Failed to extract text from the PDF.");
    }
  };

  const handleFileChange = useCallback(async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    setError(null);
    setIsProcessingFile(true);

    try {
      let extractedText = "";
      if (selectedFile.type.startsWith("image/")) extractedText = await extractTextFromImage(selectedFile);
      else if (selectedFile.type === "application/pdf") extractedText = await extractTextFromPDF(selectedFile);
      else throw new Error("Unsupported file type. Please upload a PDF or image.");

      if (!extractedText.trim()) throw new Error("Failed to extract text. The file may be empty or unreadable.");

      setFiles((prevFiles) => [...prevFiles, selectedFile]);
      setFilePreview((prevPreviews) => [...prevPreviews, { type: selectedFile.type, name: selectedFile.name, extractedText }]);
      setMessages((prevMessages) => [...prevMessages, { role: "system", content: `📂 Uploaded: ${selectedFile.name}` }]);
    } catch (error) {
      console.error("File processing error:", error);
      setError(error.message || "Failed to process the file.");
    } finally {
      setIsProcessingFile(false);
    }
  }, []);

  const handleSend = useCallback(async () => {
    if (!input.trim() && filePreview.length === 0) return;

    setIsLoading(true);
    try {
      const textToSend = input.trim();
      const extractedTextFromFiles = filePreview.map((file) => file.extractedText).join("\n\n");
      const combinedText = textToSend + (extractedTextFromFiles ? `\n\nExtracted Text:\n${extractedTextFromFiles}` : "");

      setMessages((prevMessages) => [
        ...prevMessages,
        { role: "user", content: combinedText },
        { role: "assistant", content: "" },
      ]);

      const response = await fetch("http://localhost:8080/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: combinedText }),
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      if (!response.body) throw new Error("No response body received.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let assistantMessage = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        if (chunk.trim()) {
          assistantMessage += chunk;
          setMessages((prevMessages) => [...prevMessages.slice(0, -1), { role: "assistant", content: assistantMessage }]);
        }
      }
    } catch (error) {
      console.error("Error fetching response:", error);
      setMessages((prevMessages) => [...prevMessages.slice(0, -1), { role: "assistant", content: "⚠️ Something went wrong. Please try again!" }]);
    } finally {
      setIsLoading(false);
      setInput("");
      setFiles([]);
      setFilePreview([]);
    }
  }, [input, filePreview]);

  // Logout Function
  const handleLogout = () => {
    localStorage.removeItem("users"); // Remove all users from localStorage
    navigate("/ "); // Redirect to signup page
  };

  return (
    <div className="chatbot-container">
      {/* Logout Button */}
      <button onClick={handleLogout} className="logout-button website-name">
        Verdicta
      </button>

      {error && <div className="error-message">{error}</div>}

      {/* Message Container */}
      <div className="message-container">
        <div className="chatbot-messages">
          {messages.map((msg, index) => (
            <div key={index} className={`chatbot-message ${msg.role}`}>
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          ))}
          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Container */}
      <div className="chatbot-input-container">
        <div
          className="file-upload-icon"
          onClick={() => document.getElementById("file-upload-input").click()}
          style={{ position: "absolute", left: "15px", top: "50%", transform: "translateY(-50%)" }}
        >
          <img src="/src/assets/attach1.png" alt="Upload Icon" style={{ width: "20px", height: "20px" }} />
        </div>

        {/* Text Input */}
        <input
          id="chatbot-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          className="chatbot-input"
          disabled={isLoading}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        />

        {/* Send Button */}
        <button onClick={handleSend} className="chatbot-send-button" disabled={isLoading}>
          {isLoading ? "Sending..." : "Send"}
        </button>

        {/* Hidden File Input */}
        <input
          id="file-upload-input"
          type="file"
          accept=".pdf,image/*"
          onChange={handleFileChange}
          className="file-upload-input"
          disabled={isLoading || isProcessingFile}
          style={{ display: "none" }}
        />
      </div>
    </div>
  );
};

export default Chatbot;
