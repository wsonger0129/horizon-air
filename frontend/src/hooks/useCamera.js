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
      if (!navigator.mediaDevices?.getUserMedia) {
        const isSecure = typeof window !== 'undefined' && (window.isSecureContext ?? (window.location?.protocol === 'https:' || window.location?.hostname === 'localhost'));
        throw new Error(
          isSecure
            ? 'Camera not supported in this browser.'
            : 'CAMERA_NEEDS_HTTPS'
        );
      }
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
      const message = err.message === 'CAMERA_NEEDS_HTTPS'
        ? 'Camera requires a secure connection (HTTPS).'
        : (err.message || 'Camera access failed');
      setError(message);
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
