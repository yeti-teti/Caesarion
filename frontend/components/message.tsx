"use client";

import type { Message } from "ai";
import { motion } from "framer-motion";
import { useState } from "react";

import { SparklesIcon, LoaderIcon } from "./icons";
import { Markdown } from "./markdown";
import { PreviewAttachment } from "./preview-attachment";
import { cn } from "@/lib/utils";
import { Weather } from "./weather";

import { CodeCell } from "./jupyter/CodeCell";


const ExecutionStatus = ({ 
  status, 
  toolName 
}: { 
  status: 'executing' | 'completed' | 'error';
  toolName: string;
}) => {
  const statusConfig = {
    executing: {
      icon: <LoaderIcon size={14} className="animate-spin" />,
      text: toolName === 'python_interpreter' ? 'Executing code in sandbox...' : 'Processing...',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-700',
      borderColor: 'border-blue-200'
    },
    completed: {
      icon: <SparklesIcon size={14} />,
      text: 'Execution completed',
      bgColor: 'bg-green-50',
      textColor: 'text-green-700',
      borderColor: 'border-green-200'
    },
    error: {
      icon: <span className="text-red-500">⚠</span>,
      text: 'Execution failed',
      bgColor: 'bg-red-50',
      textColor: 'text-red-700',
      borderColor: 'border-red-200'
    }
  };

  const config = statusConfig[status];

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium",
        config.bgColor,
        config.textColor,
        config.borderColor
      )}
    >
      {config.icon}
      <span>{config.text}</span>
      {status === 'executing' && (
        <div className="flex gap-1 ml-2">
          <div className="w-1 h-1 bg-current rounded-full animate-pulse" style={{animationDelay: '0ms'}} />
          <div className="w-1 h-1 bg-current rounded-full animate-pulse" style={{animationDelay: '150ms'}} />
          <div className="w-1 h-1 bg-current rounded-full animate-pulse" style={{animationDelay: '300ms'}} />
        </div>
      )}
    </motion.div>
  );
};

export const PreviewMessage = ({
  message,
  isLoading
}: {
  chatId: string;
  message: Message;
  isLoading: boolean;
}) => {
  return (
    <motion.div
      className="w-full mx-auto max-w-3xl px-4 group/message"
      initial={{ y: 5, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      data-role={message.role}
    >
      <div
        className={cn(
          "group-data-[role=user]/message:bg-primary group-data-[role=user]/message:text-primary-foreground flex gap-4 group-data-[role=user]/message:px-3 w-full group-data-[role=user]/message:w-fit group-data-[role=user]/message:ml-auto group-data-[role=user]/message:max-w-2xl group-data-[role=user]/message:py-2 rounded-xl",
        )}
      >
        {message.role === "assistant" && (
          <div className="size-8 flex items-center rounded-full justify-center ring-1 shrink-0 ring-border">
            <SparklesIcon size={14} />
          </div>
        )}

        <div className="flex flex-col gap-2 w-full">
          {message.content && !message.toolInvocations?.some(t => t.toolName === "python_interpreter") && (
            <div className="flex flex-col gap-4">
              <Markdown>{message.content as string}</Markdown>
            </div>
          )}

          {message.toolInvocations && message.toolInvocations.length > 0 && (
            <div className="flex flex-col gap-4">
              {message.toolInvocations.map((toolInvocation) => {
                const { toolName, toolCallId, state } = toolInvocation;

                if (state === "result") {
                  const { result } = toolInvocation;

                  
                  // Completion status
                  const hasError = toolName === "python_interpreter" && 
                  result.outputs?.some(
                    (output: any) => output.output_type === 'error'
                  );

                  if (toolName === "python_interpreter") {
                    console.log("Python interpreter result:", result);
                    console.log("Tool args:", toolInvocation.args);
                  }

                  return (
                    <div key={toolCallId} className="space-y-3">
                      <ExecutionStatus 
                        status={hasError ? 'error' : 'completed'} 
                        toolName={toolName} 
                      />

                      {toolName === "get_current_weather" ? (
                        <Weather weatherAtLocation={result} />
                      ) : toolName === "python_interpreter" ? (
                        <CodeCell
                          code={result.code || toolInvocation.args?.code || ""}
                          outputs={result.outputs || []}
                          executionCount={1}
                        />
                      ) : (
                        <pre className="bg-gray-50 p-3 rounded-md text-sm overflow-x-auto">
                          {JSON.stringify(result, null, 2)}
                        </pre>
                      )}
                    </div>
                  );
                }

                // Show executing status
                return (
                  <div key={toolCallId} className="space-y-3">
                    <ExecutionStatus status="executing" toolName={toolName} />
                    
                    <div className={cn({
                      skeleton: ["get_current_weather", "python_interpreter"].includes(toolName),
                    })}>
                      {toolName === "get_current_weather" ? (
                        <Weather />
                      ) : toolName === "python_interpreter" ? (
                        <motion.div 
                          className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm"
                          initial={{ opacity: 0.6 }}
                          animate={{ opacity: [0.6, 1, 0.6] }}
                          transition={{ duration: 1.5, repeat: Infinity }}
                        >
                          <div className="flex">
                            <div className="flex-shrink-0 w-14 bg-slate-50 border-r border-slate-200 flex items-center justify-center py-4">
                              <span className="text-xs text-slate-600 font-mono font-medium">In</span>
                            </div>
                            <div className="flex-1 p-4">
                              <div className="space-y-2">
                                <div className="h-4 bg-slate-200 rounded animate-pulse" />
                                <div className="h-4 bg-slate-200 rounded animate-pulse w-3/4" />
                                <div className="h-4 bg-slate-200 rounded animate-pulse w-1/2" />
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {message.experimental_attachments && (
            <div className="flex flex-row gap-2 flex-wrap">
              {message.experimental_attachments.map((attachment) => (
                <PreviewAttachment
                  key={attachment.url}
                  attachment={attachment}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export const ThinkingMessage = () => {
  const role = "assistant";

  return (
    <motion.div
      className="w-full mx-auto max-w-3xl px-4 group/message "
      initial={{ y: 5, opacity: 0 }}
      animate={{ y: 0, opacity: 1, transition: { delay: 1 } }}
      data-role={role}
    >
      <div
        className={cn(
          "flex gap-4 group-data-[role=user]/message:px-3 w-full group-data-[role=user]/message:w-fit group-data-[role=user]/message:ml-auto group-data-[role=user]/message:max-w-2xl group-data-[role=user]/message:py-2 rounded-xl",
          {
            "group-data-[role=user]/message:bg-muted": true,
          },
        )}
      >
        <div className="size-8 flex items-center rounded-full justify-center ring-1 shrink-0 ring-border">
          <SparklesIcon size={14} />
        </div>

        <div className="flex flex-col gap-2 w-full">
          <div className="flex flex-col gap-4 text-muted-foreground">
            Thinking...
          </div>
        </div>
      </div>
    </motion.div>
  );
};
