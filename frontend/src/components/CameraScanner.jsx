import React, { useEffect, useMemo, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";

const LOCAL_COOLDOWN_MS = 1000;

export function CameraScanner({ onScan }) {
  const [isSupported, setIsSupported] = useState(true);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("Idle");
  const [lastCode, setLastCode] = useState("");
  const [manualCode, setManualCode] = useState("");
  const [engine, setEngine] = useState("native");

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const rafRef = useRef(null);
  const detectorRef = useRef(null);
  const zxingReaderRef = useRef(null);
  const zxingControlsRef = useRef(null);
  const lastSeenRef = useRef({ value: "", at: 0 });
  const runningRef = useRef(false);

  useEffect(() => {
    const hasCameraApi =
      typeof navigator !== "undefined" &&
      Boolean(navigator.mediaDevices) &&
      typeof navigator.mediaDevices.getUserMedia === "function";
    setIsSupported(hasCameraApi);
    setEngine(typeof window !== "undefined" && "BarcodeDetector" in window ? "native" : "zxing");
  }, []);

  const submitManual = async () => {
    const value = manualCode.trim();
    if (!value) return;
    setStatus("Sending manual test code...");
    try {
      const response = await onScan(value);
      setLastCode(value);
      setStatus(response?.accepted ? "Accepted" : "Rejected by backend");
    } catch {
      setStatus("Failed to submit scan");
    }
  };

  const supportedFormats = useMemo(
    () => ["qr_code", "ean_13", "ean_8", "upc_a", "upc_e", "code_128", "code_39"],
    []
  );

  const stop = async () => {
    runningRef.current = false;
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (zxingControlsRef.current && typeof zxingControlsRef.current.stop === "function") {
      zxingControlsRef.current.stop();
      zxingControlsRef.current = null;
    }
    if (streamRef.current) {
      for (const track of streamRef.current.getTracks()) {
        track.stop();
      }
      streamRef.current = null;
    }
    setRunning(false);
    setStatus("Stopped");
  };

  const scanLoop = async () => {
    if (!runningRef.current || !videoRef.current || !detectorRef.current) return;

    try {
      const results = await detectorRef.current.detect(videoRef.current);
      if (results.length > 0) {
        const value = (results[0].rawValue || "").trim();
        const now = Date.now();
        const duplicate =
          value &&
          lastSeenRef.current.value === value &&
          now - lastSeenRef.current.at < LOCAL_COOLDOWN_MS;

        if (value && !duplicate) {
          lastSeenRef.current = { value, at: now };
          setLastCode(value);
          setStatus("Code detected, sending...");
          try {
            const response = await onScan(value);
            setStatus(response?.accepted ? "Accepted" : "Rejected by backend");
          } catch {
            setStatus("Failed to submit scan");
          }
        }
      }
    } catch {
      setStatus("Detection error");
    }

    rafRef.current = requestAnimationFrame(scanLoop);
  };

  const start = async () => {
    if (!isSupported) {
      setStatus("Camera API not supported in this browser");
      return;
    }

    if (!videoRef.current) {
      setStatus("Video element unavailable");
      return;
    }

    if (engine === "native") {
      try {
        const detector = new window.BarcodeDetector({ formats: supportedFormats });
        detectorRef.current = detector;
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
        });
        streamRef.current = stream;
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        runningRef.current = true;
        setRunning(true);
        setStatus("Scanning...");
        rafRef.current = requestAnimationFrame(scanLoop);
        return;
      } catch {
        // Fall through to ZXing fallback below.
        setEngine("zxing");
      }
    }

    try {
      if (!zxingReaderRef.current) {
        zxingReaderRef.current = new BrowserMultiFormatReader();
      }
      runningRef.current = true;
      setRunning(true);
      setStatus("Scanning... (ZXing)");
      zxingControlsRef.current = await zxingReaderRef.current.decodeFromConstraints(
        { video: { facingMode: { ideal: "environment" } } },
        videoRef.current,
        async (result) => {
          if (!runningRef.current || !result) {
            return;
          }
          const value = (result.getText?.() || "").trim();
          if (!value) {
            return;
          }
          const now = Date.now();
          const duplicate =
            lastSeenRef.current.value === value && now - lastSeenRef.current.at < LOCAL_COOLDOWN_MS;
          if (duplicate) {
            return;
          }

          lastSeenRef.current = { value, at: now };
          setLastCode(value);
          setStatus("Code detected, sending...");
          try {
            const response = await onScan(value);
            setStatus(response?.accepted ? "Accepted" : "Rejected by backend");
          } catch {
            setStatus("Failed to submit scan");
          }
        }
      );
    } catch {
      setStatus("Camera permission denied or unavailable");
      runningRef.current = false;
      setRunning(false);
    }
  };

  useEffect(() => {
    return () => {
      stop();
    };
  }, []);

  return (
    <section className="list-section">
      <h2>Camera Test Scanner</h2>
      <p className="scanner-help">
        Use laptop camera to scan QR/barcodes for testing without a USB scanner.
      </p>
      <div className="scanner-controls">
        <button onClick={start} disabled={running || !isSupported}>
          Start camera
        </button>
        <button onClick={stop} disabled={!running}>
          Stop camera
        </button>
      </div>
      <p className="scanner-status">Engine: {engine === "native" ? "BarcodeDetector" : "ZXing fallback"}</p>
      <div className="manual-scan">
        <input
          placeholder="Manual test code"
          value={manualCode}
          onChange={(event) => setManualCode(event.target.value)}
        />
        <button onClick={submitManual}>Submit</button>
      </div>
      <video className="scanner-video" ref={videoRef} muted playsInline />
      <p className="scanner-status">Status: {status}</p>
      {lastCode ? <p className="scanner-status">Last code: {lastCode}</p> : null}
    </section>
  );
}
