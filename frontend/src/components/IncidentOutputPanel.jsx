import React from "react";
import { MessageSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";
import IncidentBox from "./IncidentBox";

/**
 * IncidentOutputPanel
 */
const IncidentOutputPanel = ({ sessionState }) => {
  const parsedIntent = sessionState?.parsed_intent || {};

  const showSummary =
    parsedIntent?.needed_summary === true && Boolean(sessionState?.summary);

  const showKnowledgeArticle =
    parsedIntent?.needed_knowledge === true &&
    Boolean(sessionState?.knowledge_article);

  const showDraftedMail =
    parsedIntent?.needed_email === true &&
    Boolean(sessionState?.drafted_mail);

  const showSolution = Boolean(sessionState?.potential_solution);

  const hasAnyOutput =
    showSummary || showKnowledgeArticle || showDraftedMail || showSolution;

  return (
    <div className="h-full">
      {hasAnyOutput ? (
        <div className="grid grid-cols-2 grid-rows-2 gap-4 h-full">
          {showSummary && (
            <IncidentBox
              title="Summary"
              rawText={sessionState.summary}
              content={
                <div className="prose prose-invert max-w-none">
                  <ReactMarkdown>{sessionState.summary}</ReactMarkdown>
                </div>
              }
            />
          )}

          {showSolution && (
            <IncidentBox
              title="Solution Generator"
              rawText={sessionState.potential_solution}
              content={
                <div className="prose prose-invert max-w-none">
                  <ReactMarkdown>
                    {sessionState.potential_solution}
                  </ReactMarkdown>
                </div>
              }
            />
          )}

          {showKnowledgeArticle && (
            <IncidentBox
              title="Incident Article"
              rawText={sessionState.knowledge_article}
              content={
                <div className="prose prose-invert max-w-none">
                  <ReactMarkdown>
                    {sessionState.knowledge_article}
                  </ReactMarkdown>
                </div>
              }
            />
          )}

          {showDraftedMail && (
            <IncidentBox
              title="Email Generator"
              rawText={sessionState.drafted_mail}
              content={
                <div className="prose prose-invert max-w-none">
                  <ReactMarkdown>{sessionState.drafted_mail}</ReactMarkdown>
                </div>
              }
            />
          )}
        </div>
      ) : (
        <div className="flex items-center justify-center h-full bg-gray-900 rounded-lg border border-purple-500/30">
          <div className="text-center">
            <MessageSquare className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500">No incident data available yet</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default IncidentOutputPanel;
