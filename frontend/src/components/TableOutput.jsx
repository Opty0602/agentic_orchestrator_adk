import React from 'react';
import ReactMarkdown from 'react-markdown';

const TableOutput = ({ markdownTable }) => {
  if (!markdownTable) return null;

  const parseMarkdownTable = (markdown) => {
    const lines = markdown.trim().split('\n').filter(line => line.trim());
    if (lines.length < 2) return { headers: [], rows: [] };

    const headers = ['S.No', ...lines[0].split('|').map(h => h.trim()).filter(h => h)
                    .map(h => h.charAt(0).toUpperCase() + h.slice(1).toLowerCase())];
     const rows = lines.slice(2).map(line => {
      const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell);
      return cells.filter((_, idx) => idx !== 0);
    });

    return { headers, rows };
  };

  const { headers, rows } = parseMarkdownTable(markdownTable);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-purple-500/30">
            {headers.map((header, idx) => (
              <th key={idx} className="text-left p-3 text-purple-300 font-semibold">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx} className="border-b border-gray-700 hover:bg-gray-800/50">
              <td className="p-3 text-gray-300">{rowIdx + 1}</td>
              {row.map((cell, cellIdx) => (
                <td key={cellIdx} className="p-3 text-gray-300">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TableOutput;
