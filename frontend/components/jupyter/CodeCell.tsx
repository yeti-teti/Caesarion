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
    // Debug logging
    console.log("CodeCell received:", { code, outputs, executionCount });
    
    return (
      <div className={cn("border border-blue-300 rounded-lg overflow-hidden bg-blue-50 shadow-lg", className)}>
        
        <div className="flex border-b border-blue-300">
          <div className="flex-shrink-0 w-16 bg-blue-100 border-r border-blue-300 flex items-start justify-end p-2 text-sm text-blue-800 font-mono font-semibold">
            In [{executionCount || ' '}]:
          </div>
          <div className="flex-1">
            <pre className="text-sm font-mono whitespace-pre-wrap p-3 bg-blue-50 overflow-x-auto text-gray-900">
              <code className="language-python">{code}</code>
            </pre>
          </div>
        </div>

        {outputs && outputs.length > 0 && (
          <div className="flex">
            <div className="flex-shrink-0 w-16 bg-blue-100 border-r border-blue-300 flex items-start justify-end p-2 text-sm text-blue-800 font-mono font-semibold">
              Out[{executionCount || ' '}]:
            </div>
            <div className="flex-1 p-3 bg-blue-50">
              <JupyterOutput outputs={outputs} />
            </div>
          </div>
        )}
      </div>
    );
  };