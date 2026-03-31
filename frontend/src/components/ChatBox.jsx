import React, { useState } from 'react';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from "remark-gfm";

const ChatBox = ({ messages, onSendMessage, isLoading }) => {
  console.log("Chatbox:", messages)
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getAgentDisplayName = (agentName) => {
    return agentName.split("_")
                    .map(x => x.charAt(0).toUpperCase() + x.slice(1))
                    .join(" ") || 'Assistant';

  }

  const getAgentColor = (agentName) => {
    const colorMap = {
      assistant: "text-purple-400"
    }
    return colorMap[agentName] || "text-purple-400";
  }



  const getAgentLetter = (agentName) => {
    return agentName.charAt(0).toUpperCase() || "A";
}


  const getAgentBgColor = (agentName) => {
    const bgColorMap = {
      assistant: "bg-purple-500"
    };
    return bgColorMap[agentName] || "bg-purple-500";
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg border border-purple-500/30 overflow-hidden">
      <div className="p-4 border-b border-purple-500/30 flex-shrink-0">
        <h2 className="text-lg font-semibold text-purple-300">Chat Assistant</h2>
        <p className="text-xs text-gray-400 mt-1">
          Ask anything - I'll show the right view automatically
        </p>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="flex-shrink-0 mr-3">
                <div className={`w-10 h-10 rounded-full ${getAgentBgColor(msg.agent_name)} flex items-center justify-center text-white font-bold text-lg`}>
                  {getAgentLetter(msg.agent_name)}
                </div>
              </div>
            )}
            <div className={`max-w-[80%] min-w-0 ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
              {msg.role === 'assistant' && msg.agent_name && (
                <div className={`text-xs font-semibold mb-1 px-1 ${getAgentColor(msg.agent_name)}`}>
                  {getAgentDisplayName(msg.agent_name)}
                </div>
              )}
              <div
                className={`rounded-lg p-3 w-full min-w-0 ${
                  msg.role === 'user'
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-800 text-gray-200 border border-purple-500/20'
                }`}
              >
                <div className="prose prose-invert max-w-none prose-sm break-words overflow-wrap-anywhere">
                 

                  <ReactMarkdown
  remarkPlugins={[remarkGfm]}
  components={{
    pre: ({ node, ...props }) => (
      <pre className="overflow-x-auto" {...props} />
    ),
    code: ({ node, inline, ...props }) =>
      inline ? (
        <code className="break-words" {...props} />
      ) : (
        <code className="block overflow-x-auto" {...props} />
      ),
    table: ({ node, ...props }) => (
      <div className="overflow-x-auto my-2">
        <table className="table-auto border-collapse border border-gray-700 text-gray-300 w-full" {...props} />
      </div>
    ),
    th: ({ node, ...props }) => (
      <th className="border border-gray-600 bg-gray-800 px-3 py-1 text-left" {...props} />
    ),
    td: ({ node, ...props }) => (
      <td className="border border-gray-700 px-3 py-1" {...props} />
    )
  }}
>
  {msg.content}
</ReactMarkdown>

                </div>
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="flex-shrink-0 mr-3">
              <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
                <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
              </div>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 border border-purple-500/20">
              <div className="flex space-x-2">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.1}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-purple-500/30 flex-shrink-0">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about SQL queries, incidents, or anything else..."
            className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-2 border border-purple-500/30 focus:outline-none focus:border-purple-500 placeholder-gray-500"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white rounded-lg px-4 py-2 transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatBox;
