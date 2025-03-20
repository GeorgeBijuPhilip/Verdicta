import { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import * as pdfjsLib from 'pdfjs-dist';
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min?url';
import './Chatbotstyles.css';

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [file, setFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  const [error, setError] = useState(null);

  // Extract text from an image using Web Worker
  const extractTextFromImage = (imageFile) => {
    return new Promise((resolve, reject) => {
      const worker = new Worker(new URL('./tesseractWorker.js', import.meta.url), { type: 'module' });

      worker.postMessage(imageFile);

      worker.onmessage = (event) => {
        if (event.data.error) {
          reject(new Error(event.data.error));
        } else {
          resolve(event.data.text);
        }
        worker.terminate();
      };

      worker.onerror = (error) => {
        reject(new Error(error.message || 'Image processing failed'));
        worker.terminate();
      };
    });
  };

  // Extract text from a PDF file
  const extractTextFromPDF = async (pdfFile) => {
    try {
      const arrayBuffer = await pdfFile.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      let extractedText = '';

      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        extractedText += textContent.items.map((item) => item.str).join(' ');
      }

      return extractedText.trim();
    } catch (error) {
      console.error('PDF extraction error:', error);
      throw new Error('Failed to extract text from the PDF.');
    }
  };

  // Handle File Upload
  const handleFileChange = useCallback(async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    setError(null);
    setIsProcessingFile(true);
    setFile(selectedFile);

    try {
      let extractedText = '';

      if (selectedFile.type.startsWith('image/')) {
        extractedText = await extractTextFromImage(selectedFile);
      } else if (selectedFile.type === 'application/pdf') {
        extractedText = await extractTextFromPDF(selectedFile);
      } else {
        throw new Error('Unsupported file type. Please upload a PDF or image.');
      }

      if (!extractedText) {
        throw new Error('Failed to extract text. The file may be empty or unreadable.');
      }

      setFilePreview({
        type: selectedFile.type,
        name: selectedFile.name,
        extractedText: extractedText,
      });
    } catch (error) {
      console.error('File processing error:', error);
      setError(error.message || 'Failed to process the file.');
    } finally {
      setIsProcessingFile(false);
    }
  }, []);

  // Handle Sending Message to API
  const handleSend = useCallback(async () => {
    if (!input.trim() && !filePreview?.extractedText) return;

    setIsLoading(true);

    try {
      const textToSend = input.trim() || filePreview?.extractedText;
      const response = await fetch('http://localhost:8080/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: textToSend }),
      });

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.error || 'Failed to get response.');
      }

      setMessages((prevMessages) => [
        ...prevMessages,
        { role: 'user', content: textToSend },
        { role: 'assistant', content: result.answer },
      ]);
    } catch (error) {
      console.error('Error fetching response:', error);
      setMessages((prevMessages) => [
        ...prevMessages,
        { role: 'assistant', content: 'Something went wrong. Please try again!' },
      ]);
    } finally {
      setIsLoading(false);
      setInput('');
      setFile(null);
      setFilePreview(null);
    }
  }, [input, filePreview]);

  return (
    <div className="chatbot-container">
      <h1 className="chatbot-title">AI Legal Assistant</h1>
      {error && <div className="error-message">{error}</div>}
      <div className="chatbot-messages">
        {messages.map((msg, index) => (
          <div key={index} className={`chatbot-message ${msg.role}`}>
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        ))}
      </div>
      <div className="chatbot-input-container">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          className="chatbot-input"
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          className="chatbot-send-button"
          disabled={isLoading}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
      <div className="file-upload-container">
        <label className="file-upload-label">
          {isProcessingFile ? 'Processing...' : 'Upload PDF/Image'}
          <input
            type="file"
            accept=".pdf,image/*"
            onChange={handleFileChange}
            className="file-upload-input"
            disabled={isLoading || isProcessingFile}
          />
        </label>
      </div>
    </div>
  );
};

export default Chatbot;
