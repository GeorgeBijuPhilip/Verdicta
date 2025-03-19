import { createWorker } from 'tesseract.js';

const worker = await createWorker('eng', {
  logger: (m) => console.log(m), // Optional logging
});

self.onmessage = async (event) => {
  try {
    const { data } = await worker.recognize(event.data);
    self.postMessage({ text: data.text });
  } catch (error) {
    self.postMessage({ error: error.message || 'Text extraction failed' });
  }
};
