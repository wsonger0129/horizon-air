import { useState, useCallback, useEffect } from 'react';

/**
 * Safari-compatible camera access via getUserMedia.
 * Requires HTTPS or localhost. User must grant camera permission.
 */
export function useCamera() {
  const [stream, setStream] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | asking | active | denied | error

  const startCamera = useCallback(async () => {
    setStatus('asking');
    setError(null);
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      setStream(mediaStream);
      setStatus('active');
    } catch (err) {
      setError(err.message || 'Camera access failed');
      setStatus(err.name === 'NotAllowedError' ? 'denied' : 'error');
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
    setStatus('idle');
    setError(null);
  }, [stream]);

  useEffect(() => {
    return () => {
      if (stream) stream.getTracks().forEach((track) => track.stop());
    };
  }, [stream]);

  return { stream, error, status, startCamera, stopCamera };
}
