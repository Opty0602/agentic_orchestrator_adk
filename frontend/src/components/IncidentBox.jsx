import React, { useRef, useState, useEffect } from "react";
import { Maximize2, Minimize2, Copy, Check } from "lucide-react";

const IncidentBox = ({ title, rawText, content }) => {
  const boxRef = useRef(null);
  const copiedRef = useRef(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === boxRef.current);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener(
        "fullscreenchange",
        handleFullscreenChange
      );
    };
  }, []);

  const toggleFullscreen = () => {
    if (!boxRef.current) return;

    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      boxRef.current.requestFullscreen();
    }
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(rawText || "");
      copiedRef.current = true;
      setTimeout(() => (copiedRef.current = false), 1500);
    } catch (e) {
      console.error("Copy failed", e);
    }
  };

  return (
    <div
      ref={boxRef}
      className="bg-gray-900 rounded-lg border border-purple-500/30 flex flex-col overflow-hidden"
    >
      <div className="flex items-center justify-between p-4 border-b border-purple-500/30">
        <h3 className="text-md font-semibold text-purple-300">{title}</h3>

        <div className="flex items-center gap-3">
          <button
            onClick={copyToClipboard}
            className="text-purple-400 hover:text-purple-300"
            title="Copy to clipboard"
          >
            {copiedRef.current ? (
              <Check className="w-4 h-4" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>

          <button
            onClick={toggleFullscreen}
            className="text-purple-400 hover:text-purple-300"
            title="Toggle fullscreen"
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 text-gray-300 text-sm whitespace-pre-wrap">
        {typeof content === "string" ? <p>{content}</p> : content}
      </div>
    </div>
  );
};

export default IncidentBox;
