import { useState, useEffect, useRef } from 'react';

const HEARTBEAT_MS = 1000;
const RTT_DEGRADED_MS = 800;
const CONSECUTIVE_FAILURES_LOST = 3;

/**
 * 1 s heartbeat to Pi /api/ping. Computes RTT and connection quality (good / degraded / lost).
 */
export function useConnectionStrength(piBaseUrl) {
  const [quality, setQuality] = useState('lost');
  const [rttMs, setRttMs] = useState(null);
  const [consecutiveFailures, setConsecutiveFailures] = useState(0);
  const [lastSuccessAt, setLastSuccessAt] = useState(null);
  const failuresRef = useRef(0);

  useEffect(() => {
    if (!piBaseUrl) {
      setQuality('lost');
      setRttMs(null);
      setConsecutiveFailures(0);
      setLastSuccessAt(null);
      failuresRef.current = 0;
      return;
    }

    let cancelled = false;

    const ping = async () => {
      const start = Date.now();
      try {
        const res = await fetch(`${piBaseUrl}/api/ping`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        const ts = data?.ts;
        const rtt = typeof ts === 'number' ? Math.round(Date.now() - start) : null;
        if (rtt !== null) {
          setRttMs(rtt);
          // Send to backend so droneMain can use RTT for proximity fallback
          try {
            fetch(`${piBaseUrl}/heartbeat`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ ts: data?.ts ?? Date.now() / 1000, rtt_ms: rtt }),
            }).catch(() => {});
          } catch (_) {}
        }
        setLastSuccessAt(Date.now());
        failuresRef.current = 0;
        setConsecutiveFailures(0);
        const q =
          failuresRef.current >= CONSECUTIVE_FAILURES_LOST
            ? 'lost'
            : rtt !== null && rtt > RTT_DEGRADED_MS
              ? 'degraded'
              : 'good';
        setQuality(q);
      } catch (e) {
        if (cancelled) return;
        failuresRef.current += 1;
        setConsecutiveFailures(failuresRef.current);
        setLastSuccessAt((prev) => prev);
        setQuality(failuresRef.current >= CONSECUTIVE_FAILURES_LOST ? 'lost' : 'degraded');
        setRttMs(null);
      }
    };

    ping();
    const interval = setInterval(ping, HEARTBEAT_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [piBaseUrl]);

  return { quality, rttMs, consecutiveFailures, lastSuccessAt };
}
