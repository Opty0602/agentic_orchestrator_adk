import React, { useState } from "react";
import { Database, MessageSquare } from "lucide-react";
import ChatBox from "./components/ChatBox";
import SQLOutputPanel from "./components/SQLOutputPanel";
import IncidentOutputPanel from "./components/IncidentOutputPanel";
import logo from "./components/logo.png";

const App = () => {
  const [currentPage, setCurrentPage] = useState("sql");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionState, setSessionState] = useState(null);

  const API_BASE_URL = "http://localhost:8001";

  const hasAnyOutputData = (state) =>
    !!(
      state?.s_retreived_data ||
      state?.s_generated_intuition ||
      state?.summary ||
      state?.knowledge_article ||
      state?.potential_solution ||
      state?.drafted_mail
    );

  const handleSendMessage = async (message) => {
    // Add user message with agent_name as null
    setMessages((prev) => [
      ...prev,
      { role: "user", content: message, agent_name: null },
    ]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_message: message }),
      });

      const data = await res.json();

      if (data.success) {
        console.log(data);
        // Define allowed model names
        const allowedModelNames = [
          "Manager",
          "incident_management_agent",
          "sql_agent",
          "feedback_agent",
          ""
        ];

        // Iterate over the responses array and add each to messages
        const newMessages = data.responses.map((responseObj, index) => {
          const botResponse = Array.isArray(responseObj.response)
            ? responseObj.response.join("\n")
            : responseObj.response;

          // Ensure the model_name is valid
          const agentName = allowedModelNames.includes(responseObj.model_name)
            ? responseObj.model_name
            : "assistant"; // Default to "assistant" if not valid

          return {
            role: "assistant",
            content: botResponse,
            agent_name: agentName === "" ?  "Assistant": agentName ,
          };
        });

        // Add all the responses to the state
        setMessages((prev) => [...prev, ...newMessages]);

        if (data.session_state) setSessionState(data.session_state);

        if (data.model_name === "sql_agent") {
          setCurrentPage("sql");
        } else if (data.model_name === "incident_management_agent") {
          setCurrentPage("incident");
        }
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${data.error}`,
            agent_name: "assistant",
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err.message}`,
          agent_name: "assistant",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-screen bg-gray-950 text-white flex flex-col">
      <header className="bg-gray-900 border-b border-purple-500/30 p-4 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <img
            src={logo}
            alt="logo"
            className="w-10 h-10 rounded-full object-cover"
          />
          <h1 className="text-2xl font-bold text-purple-400">Agentic Orchestrator</h1>
        </div>
        <div className="flex space-x-2 bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setCurrentPage("sql")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md ${
              currentPage === "sql"
                ? "bg-purple-600 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Database className="w-4 h-4" />
            <span>SQL View</span>
          </button>
          <button
            onClick={() => setCurrentPage("incident")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md ${
              currentPage === "incident"
                ? "bg-purple-600 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Incident View</span>
          </button>
        </div>
      </header>

      <main className="flex-1 p-4 overflow-hidden">
        {!hasAnyOutputData(sessionState) ? (
          <div className="h-full flex items-center justify-center">
            <div className="w-full max-w-4xl h-full">
              <ChatBox
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
              />
            </div>
          </div>
        ) : (
          <div className="h-full flex gap-4">
            <div className="w-96 flex-shrink-0">
              <ChatBox
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
              />
            </div>
            <div className="flex-1">
              {currentPage === "sql" ? (
                <SQLOutputPanel sessionState={sessionState} />
              ) : (
                <IncidentOutputPanel sessionState={sessionState} />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
