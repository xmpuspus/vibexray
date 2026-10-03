};

const hasSuspiciousContent = async (file: File): Promise<boolean> => {
  // Basic check for suspicious content in file headers
  const buffer = await file.slice(0, 512).arrayBuffer();
  const bytes = new Uint8Array(buffer);
  
  // Check for common script tags or suspicious patterns
  const content = new TextDecoder('utf-8', { fatal: false }).decode(bytes);
  const suspiciousPatterns = [
    '<script',
    'javascript:',
    'data:text/html',
    'vbscript:',
    'onload=',
    'onerror=',
    'eval(',
    'document.cookie'
  ];
  
  return suspiciousPatterns.some(pattern => 
    content.toLowerCase().includes(pattern.toLowerCase())
  );
};

export const sanitizeFileName = (fileName: string): string => {
  // Remove or replace dangerous characters
  return fileName
    .replace(/[^a-zA-Z0-9.-]/g, '_') // Replace non-alphanumeric chars with underscore
    .replace(/_{2,}/g, '_') // Replace multiple underscores with single
    .replace(/^_+|_+$/g, '') // Remove leading/trailing underscores
