import { useState } from 'react';
import { toast } from 'sonner';

export const useFileUpload = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const uploadFile = async (file: File, sessionId: string | null): Promise<any> => {
    // Validate inputs
    if (!sessionId) {
      toast.error('No session found. Please refresh the page.');
      throw new Error('Session ID is required');
    }

    if (!file) {
      toast.error('No file selected');
      throw new Error('File is required');
    }

    // Validate file size
    const maxSize = 10 * 1024 * 1024 * 1024; 
    if (file.size > maxSize) {
      toast.error('File too large.');
      throw new Error('File too large');
    }

    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const progress = (e.loaded / e.total) * 100;
          setUploadProgress(progress);
        }
      };

      // Handle successful completion
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const result = JSON.parse(xhr.response);
            toast.success(`File "${result.filename}" uploaded successfully!`);
            setUploadProgress(100);
            
            // Auto-clear progress after success
            setTimeout(() => {
              setIsUploading(false);
              setUploadProgress(0);
            }, 1000);
            
            resolve(result);
          } catch (parseError) {
            setIsUploading(false);
            setUploadProgress(0);
            toast.error('Invalid response from server');
            reject(new Error('Invalid response format'));
          }
        } else {
          setIsUploading(false);
          setUploadProgress(0);
          toast.error(`Upload failed: ${xhr.statusText}`);
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      };

      // Handle network errors
      xhr.onerror = () => {
        setIsUploading(false);
        setUploadProgress(0);
        toast.error('Network error during upload');
        reject(new Error('Network error'));
      };

      // Handle aborted uploads
      xhr.onabort = () => {
        setIsUploading(false);
        setUploadProgress(0);
        toast.error('Upload cancelled');
        reject(new Error('Upload cancelled'));
      };

      // Send the request
      xhr.open('POST', `/api/sandboxes/upload?session_id=${sessionId}`);
      xhr.send(formData);
    });
  };

  const resetUpload = () => {
    setIsUploading(false);
    setUploadProgress(0);
  };

  return {
    isUploading,
    uploadProgress,
    uploadFile,
    resetUpload,
  };
};