"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { JupyterOutput } from "./JupyterOutput";

interface CodeCellProps {
    code: string;
    outputs: any[];
    executionCount?: number;
    className?: string;
}

export const CodeCell: React.FC<CodeCellProps> = ({ 
    code, 
    outputs, 
    executionCount, 
    className 
  }) => {

    console.log("CodeCell received:", { code, outputs, executionCount });
    
    return (
      <div className={cn("border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm", className)}>
        
        {/* Input Section */}
        <div className="flex">
          <div className="flex-shrink-0 w-14 bg-slate-50 border-r border-slate-200 flex items-start justify-center pt-3 pb-2">
            <span className="text-xs text-slate-600 font-mono font-medium">
              In
            </span>
          </div>
          <div className="flex-1">
            <pre className="text-sm font-mono whitespace-pre-wrap p-4 bg-white overflow-x-auto text-slate-900 leading-relaxed">
              <code className="language-python">{code}</code>
            </pre>
          </div>
        </div>

        {/* Output Section */}
        {outputs && outputs.length > 0 && (
          <div className="flex border-t border-slate-200">
            <div className="flex-shrink-0 w-14 bg-slate-50 border-r border-slate-200 flex items-start justify-center pt-3 pb-2">
              <span className="text-xs text-slate-600 font-mono font-medium">
                Out
              </span>
            </div>
            <div className="flex-1 p-4 bg-slate-25">
              <JupyterOutput outputs={outputs} />
            </div>
          </div>
        )}
      </div>
    );
  };