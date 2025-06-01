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
  <pre className={cn(
    "text-sm font-mono whitespace-pre-wrap p-3 rounded-md border",
    output.name === "stderr" ? "bg-red-100 text-red-900 border-red-300" : "bg-white text-gray-900 border-blue-200"
  )}>
    {output.text}
  </pre>
);

const ExecuteResultOutput: React.FC<OutputComponentProps> = ({ output }) => {
  const { data } = output;
  
  // Handle different MIME types
  if (data['text/html']) {
    return (
      <div 
        className="border border-blue-200 rounded-md p-3 bg-white shadow-sm"
        dangerouslySetInnerHTML={{ __html: data['text/html'] }}
      />
    );
  }
  
  if (data['image/png']) {
    return (
      <div className="flex justify-center p-3 bg-white rounded-md border border-blue-200 shadow-sm">
        <img 
          src={`data:image/png;base64,${data['image/png']}`}
          alt="Python output"
          className="max-w-full h-auto rounded-md"
        />
      </div>
    );
  }
  
  if (data['image/jpeg']) {
    return (
      <div className="flex justify-center p-3 bg-white rounded-md border border-blue-200 shadow-sm">
        <img 
          src={`data:image/jpeg;base64,${data['image/jpeg']}`}
          alt="Python output"
          className="max-w-full h-auto rounded-md"
        />
      </div>
    );
  }
  
  if (data['text/plain']) {
    return (
      <pre className="text-sm font-mono whitespace-pre-wrap p-3 bg-white text-gray-900 rounded-md border border-blue-200 shadow-sm">
        {data['text/plain']}
      </pre>
    );
  }
  
  // Fallback for other data types
  return (
    <pre className="text-sm font-mono whitespace-pre-wrap p-3 bg-white text-gray-900 rounded-md border border-blue-200 shadow-sm">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
};

const DisplayDataOutput: React.FC<OutputComponentProps> = ({ output }) => {
  return <ExecuteResultOutput output={output} />;
};

const ErrorOutput: React.FC<OutputComponentProps> = ({ output }) => (
  <div className="bg-red-100 border border-red-300 p-3 rounded-md shadow-sm">
    <div className="text-red-900 font-semibold mb-2">
      {output.ename}: {output.evalue}
    </div>
    <pre className="text-sm font-mono text-red-800 whitespace-pre-wrap">
      {output.traceback.join('\n')}
    </pre>
  </div>
);

export const JupyterOutput: React.FC<JupyterOutputProps> = ({ outputs, className }) => {
  // Debug logging
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
              <pre key={key} className="text-sm font-mono whitespace-pre-wrap p-3 bg-white text-gray-900 rounded-md border border-blue-200 shadow-sm">
                {JSON.stringify(output, null, 2)}
              </pre>
            );
        }
      })}
    </div>
  );
};
