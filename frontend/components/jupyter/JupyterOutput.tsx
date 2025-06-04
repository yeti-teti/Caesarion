"use client";

import React from 'react';
import { cn } from '@/lib/utils';

interface JupyterOutputProps {
  outputs: any[];
  className?: string;
}

interface OutputComponentProps {
  output: any;
}

const StreamOutput: React.FC<OutputComponentProps> = ({ output }) => (
  <div className="overflow-x-auto">
    <pre className={cn(
      "text-sm font-mono whitespace-pre p-3 rounded-lg border min-w-fit",
      output.name === "stderr" 
        ? "bg-red-50 text-red-900 border-red-200" 
        : "bg-blue-50 text-gray-900 border-blue-200"
    )}>
      {output.text}
    </pre>
  </div>
);

const ExecuteResultOutput: React.FC<OutputComponentProps> = ({ output }) => {
  const { data } = output;
  
  // Handle different MIME types
  if (data['text/html']) {
    return (
      <div className="overflow-x-auto">
        <div 
          className="border border-blue-200 rounded-lg p-3 bg-blue-50 shadow-sm min-w-fit text-gray-900"
          dangerouslySetInnerHTML={{ __html: data['text/html'] }}
          style={{ color: '#111827' }}
        />
      </div>
    );
  }
  
  if (data['image/png']) {
    return (
      <div className="flex justify-center p-3 bg-blue-50 rounded-lg border border-blue-200 shadow-sm overflow-x-auto">
        <img 
          src={`data:image/png;base64,${data['image/png']}`}
          alt="Python output"
          className="max-w-none h-auto rounded-lg"
          style={{ maxWidth: 'none' }}
        />
      </div>
    );
  }
  
  if (data['image/jpeg']) {
    return (
      <div className="flex justify-center p-3 bg-blue-50 rounded-lg border border-blue-200 shadow-sm overflow-x-auto">
        <img 
          src={`data:image/jpeg;base64,${data['image/jpeg']}`}
          alt="Python output"
          className="max-w-none h-auto rounded-lg"
          style={{ maxWidth: 'none' }}
        />
      </div>
    );
  }
  
  if (data['text/plain']) {
    return (
      <div className="overflow-x-auto">
        <pre className="text-sm font-mono whitespace-pre p-3 bg-blue-50 text-gray-900 rounded-lg border border-blue-200 min-w-fit font-semibold">
          {data['text/plain']}
        </pre>
      </div>
    );
  }
  
  // Fallback for other data types
  return (
    <div className="overflow-x-auto">
      <pre className="text-sm font-mono whitespace-pre p-3 bg-blue-50 text-gray-900 rounded-lg border border-blue-200 min-w-fit font-semibold">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
};

const DisplayDataOutput: React.FC<OutputComponentProps> = ({ output }) => {
  return <ExecuteResultOutput output={output} />;
};

const ErrorOutput: React.FC<OutputComponentProps> = ({ output }) => (
  <div className="bg-red-50 border border-red-200 p-3 rounded-lg shadow-sm">
    <div className="text-red-900 font-semibold mb-2 text-sm flex items-center gap-2">
      <span className="text-red-500">⚠️</span>
      <span>{output.ename}: {output.evalue}</span>
    </div>
    <div className="overflow-x-auto">
      <pre className="text-xs font-mono text-red-800 whitespace-pre min-w-fit">
        {output.traceback.join('\n')}
      </pre>
    </div>
  </div>
);

export const JupyterOutput: React.FC<JupyterOutputProps> = ({ outputs, className }) => {

  console.log("JupyterOutput received outputs:", outputs);
  
  if (!outputs || outputs.length === 0) {
    console.log("No outputs to display");
    return null;
  }

  return (
    <div className={cn("space-y-3", className)}>
      {outputs.map((output, index) => {
        const key = `output-${index}`;
        
        switch (output.output_type) {
          case 'stream':
            return <StreamOutput key={key} output={output} />;
          case 'execute_result':
            return <ExecuteResultOutput key={key} output={output} />;
          case 'display_data':
            return <DisplayDataOutput key={key} output={output} />;
          case 'error':
            return <ErrorOutput key={key} output={output} />;
          default:
            return (
              <div key={key} className="overflow-x-auto">
                <pre className="text-sm font-mono whitespace-pre p-3 bg-blue-50 text-gray-900 rounded-lg border border-blue-200 min-w-fit font-semibold">
                  {JSON.stringify(output, null, 2)}
                </pre>
              </div>
            );
        }
      })}
    </div>
  );
};