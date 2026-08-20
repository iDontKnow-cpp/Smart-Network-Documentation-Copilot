import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Loader2, Server, Globe, Cpu, Paperclip, X } from 'lucide-react';

export default function App() {
  const [chatId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [agentStatus, setAgentStatus] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [images, setImages] = useState([]);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => () => {
    fetch(`api/chat/${chatId}/uploads`, { method: 'DELETE', keepalive: true }).catch(() => {});
  }, [chatId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, agentStatus]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() && images.length === 0) return;

    const userMessage = { role: 'user', content: input };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);
    setAgentStatus('Initializing connection...');

    try {
      const response = await fetch("api/chat", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          history: newMessages.map((msg) => ({ role: msg.role, content: msg.content })),
          chat_id: chatId,
          images: images.map((image) => image.filename),
        }),
      });

      if (!response.body) throw new Error('ReadableStream not supported.');

      // Set up the stream reader
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '').trim();
              
              if (dataStr === '[DONE]') {
                setIsLoading(false);
                setAgentStatus('');
                continue;
              }

              try {
                const parsed = JSON.parse(dataStr);
                
                if (parsed.type === 'status') {
                  // Update the live agent status badge
                  setAgentStatus(parsed.message);
                } else if (parsed.type === 'result') {
                  // Append the final answer to the chat
                  setMessages((prev) => [
                    ...prev,
                    { role: 'assistant', content: parsed.message },
                  ]);
                  setAgentStatus('');
                  setIsLoading(false);
                }
              } catch (err) {
                console.error("Error parsing stream data:", err);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Fetch error:', error);
      setAgentStatus('Error: Connection failed.');
      setIsLoading(false);
    }
  };

  const uploadFiles = async (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    if (files.length === 0) return;

    setIsUploading(true);
    setUploadStatus(`Uploading ${files.length} file${files.length === 1 ? '' : 's'}...`);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('chat_id', chatId);
        const response = await fetch('api/upload', { method: 'POST', body: formData });
        const responseText = await response.text();
        let result;
        try {
          result = responseText ? JSON.parse(responseText) : {};
        } catch {
          throw new Error(`Server returned ${response.status}: ${responseText || 'empty response'}`);
        }
        if (!response.ok) throw new Error(result.detail || 'Upload failed.');
        if (result.kind === 'image') setImages((current) => [...current, result]);
        setUploadStatus(result.kind === 'pdf'
          ? `${result.filename} stored temporarily in this chat and queued for indexing.`
          : `${result.filename} attached to this chat.`);
      }
    } catch (error) {
      setUploadStatus(`Upload error: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Helper to pick an icon based on what the agent is doing
  const getStatusIcon = () => {
    if (agentStatus.includes('Local')) return <Server className="w-4 h-4 animate-pulse text-blue-400" />;
    if (agentStatus.includes('Web')) return <Globe className="w-4 h-4 animate-pulse text-green-400" />;
    return <Cpu className="w-4 h-4 animate-pulse text-yellow-400" />;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <div className="mx-auto flex h-screen max-w-6xl flex-col p-4 md:p-6">
        <div className="flex flex-1 flex-col overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-950/80 shadow-2xl shadow-slate-950/40 backdrop-blur-xl">
          {/* Header */}
          <header className="px-6 py-5 border-b border-slate-800 bg-slate-950/70 backdrop-blur-xl">
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="grid h-11 w-11 place-items-center rounded-2xl bg-indigo-600/15 text-indigo-400 ring-1 ring-indigo-500/30">
                    <Server className="w-5 h-5" />
                  </div>
                  <div>
                    <h1 className="text-3xl font-semibold tracking-tight text-white">Infrastructure RAG Agent</h1>
                    <p className="text-slate-400 text-sm mt-1">Multi-vector routing across local AWS docs and external APIs.</p>
                  </div>
                </div>
              </div>
            </div>
          </header>

          {/* Chat Area */}
          <main className="flex-1 min-h-0 overflow-y-auto px-6 py-5">
            <div className="space-y-4">
            {messages.length === 0 && (
              <div className="flex min-h-[160px] flex-col items-center justify-center text-slate-500 space-y-2 rounded-3xl border border-slate-800 bg-slate-950/70 px-5 py-6">
                <Cpu className="w-9 h-9 text-slate-500" />
                <p className="text-sm">Agent standing by. Ask an architecture question.</p>
              </div>
            )}

            {messages.map((msg, index) => {
              const normalizedContent = msg.content.replace(/\n{2,}/g, '\n\n').trim();
              return (
                <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[90%] rounded-[1.75rem] px-5 py-4 shadow-lg ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-indigo-500/20'
                      : 'bg-slate-900 text-slate-100 border border-slate-700 shadow-slate-950/30'
                  }`}>

                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      className="text-base text-slate-100"
                      components={{
                        p: ({ node, ...props }) => (
                          <p className="my-1 leading-snug text-base" {...props} />
                        ),
                        ul: ({ node, ...props }) => (
                          <ul className="list-disc list-inside space-y-1 pl-4" {...props} />
                        ),
                        ol: ({ node, ...props }) => (
                          <ol className="list-decimal list-inside space-y-1 pl-4" {...props} />
                        ),
                        li: ({ node, ...props }) => (
                          <li className="text-base leading-snug" {...props} />
                        ),
                      }}
                    >
                      {normalizedContent}
                    </ReactMarkdown>
                  </div>
                </div>
              );
            })}

        {/* Live Agent Status Widget */}
        {isLoading && agentStatus && (
          <div className="flex justify-start">
            <div className="flex items-center gap-3 bg-slate-900/80 border border-indigo-500/20 text-indigo-200 px-4 py-2 rounded-full text-sm font-medium tracking-tight w-fit shadow-sm shadow-indigo-500/10">
              {getStatusIcon()}
              {agentStatus}
              <Loader2 className="w-3 h-3 animate-spin ml-2" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
            </div>
          </main>

          {/* Input Area */}
          <div className="border-t border-slate-800 px-5 py-4">
            {images.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {images.map((image) => (
                  <div key={image.filename} className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-sm text-slate-300">
                    <span>{image.filename}</span>
                    <button type="button" onClick={() => setImages((current) => current.filter((item) => item.filename !== image.filename))} aria-label={`Remove ${image.filename}`} className="text-slate-400 hover:text-white">
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            {uploadStatus && <p className="mb-2 text-xs text-slate-400">{uploadStatus}</p>}
            <form onSubmit={sendMessage} className="flex items-center gap-3">
              <input ref={fileInputRef} type="file" accept="application/pdf,image/jpeg,image/png,image/gif,image/webp" multiple onChange={uploadFiles} className="hidden" />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading || isUploading}
                aria-label="Attach PDF or image"
                title="Attach PDF or image"
                className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-3xl border border-slate-800 bg-slate-950/80 text-slate-300 transition hover:border-indigo-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isUploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Paperclip className="h-5 w-5" />}
              </button>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="e.g. What is the MTU for an AWS Transit Gateway?"
                disabled={isLoading}
                className="w-full rounded-3xl border border-slate-800 bg-slate-950/80 px-4 py-4 text-lg text-slate-100 placeholder:text-slate-500 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
              />
              <button
                type="submit"
                disabled={isLoading || isUploading || (!input.trim() && images.length === 0)}
                className="inline-flex h-12 w-12 items-center justify-center rounded-3xl bg-indigo-600 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}