"use client";

import { useState, useEffect } from "react";

import { PreviewMessage, ThinkingMessage } from "@/components/message";
import { MultimodalInput } from "@/components/multimodal-input";
import { Overview } from "@/components/overview";
import { useScrollToBottom } from "@/hooks/use-scroll-to-bottom";
import { ToolInvocation } from "ai";
import { useChat } from "ai/react";
import { toast } from "sonner";

export function Chat() {
  const chatId = "001";

  const [sessionId, setSessionId] = useState<string>("");
  const [sandboxStatus, setSandboxStatus] = useState<"initializing" | "ready" | "failed" | "unknown">("unknown");

  // Initialize session and create sandbox pod
  const initializeSession = async (sessionId: string) => {
    try {
      setSandboxStatus("initializing");
      
      const response = await fetch(`/api/sessions/${sessionId}/initialize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Session initialization result:', result);
        
        if (result.status === 'created' || result.status === 'exists') {
          setSandboxStatus("ready");
        } else {
          setSandboxStatus("failed");
        }
      } else {
        console.error('Session initialization failed:', response.status);
        setSandboxStatus("failed");
      }
    } catch (error) {
      console.error('Session initialization error:', error);
      setSandboxStatus("failed");
    }
  };

  useEffect(() => {
    let id = localStorage.getItem('session_id');
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem('session_id', id);
    }
    setSessionId(id);
    
    // Initialize session and create sandbox pod
    if (id) {
      initializeSession(id);
    }
  }, []);

  const {
    messages,
    setMessages,
    handleSubmit,
    input,
    setInput,
    append,
    isLoading,
    stop,
  } = useChat({
    maxSteps: 4,
    body: {
      session_id: sessionId
    },
    onError: (error) => {
      if (error.message.includes("Too many requests")) {
        toast.error(
          "You are sending too many messages. Please try again later.",
        );
      }
    },
  });

  const [messagesContainerRef, messagesEndRef] = useScrollToBottom<HTMLDivElement>();

  if (!sessionId) {
    return (
      <div className="flex flex-col min-w-0 h-[calc(100dvh-52px)] bg-background items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <div className="text-muted-foreground">Initializing session...</div>
        </div>
      </div>
    );
  }

  const getSandboxStatusColor = () => {
    switch (sandboxStatus) {
      case "ready": return "bg-green-400";
      case "initializing": return "bg-yellow-400 animate-pulse";
      case "failed": return "bg-red-400";
      default: return "bg-gray-400";
    }
  };

  const getSandboxStatusText = () => {
    switch (sandboxStatus) {
      case "ready": return "Ready";
      case "initializing": return "Starting...";
      case "failed": return "Failed";
      default: return "Unknown";
    }
  };

  return (
    <div className="flex flex-col min-w-0 h-[calc(100dvh-52px)] bg-background relative">

      {/* Session indicator */}
      <div className="absolute top-4 left-4 z-10">
        <div className="bg-white/90 backdrop-blur-sm border border-slate-200 rounded-lg px-3 py-1.5 shadow-sm">
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${getSandboxStatusColor()}`}></div>
              <span>Session: {sessionId.slice(-8)} • {getSandboxStatusText()}</span>
            </div>
            {isLoading && (
              <div className="flex items-center gap-1 ml-2">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div
        ref={messagesContainerRef}
        className="flex flex-col min-w-0 gap-6 flex-1 overflow-y-scroll pt-6 pb-4"
      >
        {messages.length === 0 && <Overview />}

        {messages.map((message, index) => (
          <PreviewMessage
            key={message.id}
            chatId={chatId}
            message={message}
            isLoading={isLoading && messages.length - 1 === index}
          />
        ))}

        {isLoading &&
          messages.length > 0 &&
          messages[messages.length - 1].role === "user" && <ThinkingMessage />}

        <div
          ref={messagesEndRef}
          className="shrink-0 min-w-[24px] min-h-[24px]"
        />
      </div>

      <form className="flex mx-auto px-4 bg-background pb-4 md:pb-6 gap-2 w-full md:max-w-4xl">
        <MultimodalInput
          chatId={chatId}
          input={input}
          setInput={setInput}
          handleSubmit={handleSubmit}
          isLoading={isLoading}
          stop={stop}
          messages={messages}
          setMessages={setMessages}
          append={append}
        />
      </form>
    </div>
  );
}