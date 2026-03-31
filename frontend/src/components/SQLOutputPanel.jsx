

import React, { useState } from "react";
import { Maximize2, Minimize2, Download } from "lucide-react";
import * as XLSX from "xlsx";
import { saveAs } from "file-saver";
import TableOutput from "./TableOutput";
import ReactMarkdown from 'react-markdown';

const SQLOutputPanel = ({ sessionState }) => {
  const [isFullScreen, setIsFullScreen] = useState(false);
  const hasData =
    sessionState?.s_retreived_data || sessionState?.s_generated_intuition;

  // ✅ Function to trigger Excel (.xlsx) download
  const handleDownload = () => {
    if (!sessionState?.s_retreived_data) return;

    const markdown = sessionState.s_retreived_data.trim();
    const lines = markdown.split("\n").filter((line) => line.trim());
    if (lines.length < 2) return;

    // Extract headers and rows from markdown table
    const headers = lines[0]
      .split("|")
      .map((h) => h.trim())
      .filter((h) => h);
    const rows = lines.slice(2).map((line) => {
      const cells = line
        .split("|")
        .map((cell) => cell.trim())
        .filter((cell) => cell);
      return cells;
    });

    // Convert markdown data to JSON format (required for xlsx)
    const jsonData = rows.map((row) => {
      const rowObj = {};
      headers.forEach((header, idx) => {
        rowObj[header] = row[idx] || "";
      });
      return rowObj;
    });

    // Create Excel workbook
    const worksheet = XLSX.utils.json_to_sheet(jsonData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Query Output");

    // Generate Excel file and trigger download
    const excelBuffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
    const blob = new Blob([excelBuffer], { type: "application/octet-stream" });
    saveAs(blob, "query_output.xlsx");
  };

  return (
    <div
      className={`flex flex-col space-y-4 h-full ${
        isFullScreen ? "fixed inset-0 z-50 bg-gray-900 p-4" : ""
      }`}
    >
      <div className="flex-1 bg-gray-900 rounded-lg border border-purple-500/30 overflow-hidden flex flex-col">
        {/* Header Section */}
        <div className="p-3 border-b border-purple-500/30 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-purple-300">
            Query Output
          </h2>

          <div className="flex items-center space-x-3">
            {/* 🔄 Fullscreen toggle */}
            <button
              onClick={() => setIsFullScreen(!isFullScreen)}
              className="text-purple-400 hover:text-purple-300 transition-all duration-300 transform hover:scale-110 hover:bg-purple-500/20 hover:shadow-[0_0_10px_rgba(168,85,247,0.6)] p-1 rounded-full cursor-pointer"
              title={isFullScreen ? "Exit Fullscreen" : "Enter Fullscreen"}
            >
              {isFullScreen ? (
                <Minimize2 className="w-5 h-5" />
              ) : (
                <Maximize2 className="w-5 h-5" />
              )}
            </button>

            {/* ⬇️ Download Excel */}
            <button
              onClick={handleDownload}
              className="text-purple-400 hover:text-purple-300 transition-all duration-300 transform hover:scale-110 hover:bg-purple-500/20 hover:shadow-[0_0_10px_rgba(168,85,247,0.6)] p-1 rounded-full cursor-pointer"
              title="Download Excel"
            >
              <Download className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Table Output */}
        <div className="flex-1 overflow-auto p-4">
          {sessionState?.s_retreived_data ? (
            <TableOutput markdownTable={sessionState.s_retreived_data} />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              No query results yet
            </div>
          )}
        </div>
      </div>

      {/* Output Reasoning */}
      {!isFullScreen && (
        <div className="bg-gray-900 rounded-lg border border-purple-500/30 p-4 max-h-48 overflow-auto">
          <h3 className="text-md font-semibold text-purple-300 mb-2">
            Output Reasoning
          </h3>
          <div className="text-gray-300 text-sm">
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown>
                {sessionState?.s_generated_intuition || "No reasoning available yet"}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SQLOutputPanel;
