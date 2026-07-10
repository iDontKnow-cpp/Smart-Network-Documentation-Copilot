import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Server, Globe, Cpu } from 'lucide-react';

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [agentStatus, setAgentStatus] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, agentStatus]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setAgentStatus('Initializing connection...');

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage.content }),
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

  // Helper to pick an icon based on what the agent is doing
  const getStatusIcon = () => {
    if (agentStatus.includes('Local')) return <Server className="w-4 h-4 animate-pulse text-blue-400" />;
    if (agentStatus.includes('Web')) return <Globe className="w-4 h-4 animate-pulse text-green-400" />;
    return <Cpu className="w-4 h-4 animate-pulse text-yellow-400" />;
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4 md:p-6">
      
      {/* Header */}
      <header className="mb-6 pb-4 border-b border-slate-700">
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <Server className="w-6 h-6 text-indigo-500" />
          Infrastructure RAG Agent
        </h1>
        <p className="text-slate-400 text-sm mt-1">Multi-vector routing across local AWS docs and external APIs.</p>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto mb-6 space-y-4 pr-2 custom-scrollbar">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-4">
            <Cpu className="w-12 h-12 text-slate-700" />
            <p>Agent standing by. Ask an architecture question.</p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-lg p-4 ${
              msg.role === 'user' 
                ? 'bg-indigo-600 text-white' 
                : 'bg-slate-800 text-slate-200 border border-slate-700 shadow-md'
            }`}>
              {/* If it's the assistant, we could add markdown parsing here later */}
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
            </div>
          </div>
        ))}

        {/* Live Agent Status Widget */}
        {isLoading && agentStatus && (
          <div className="flex justify-start">
            <div className="flex items-center gap-3 bg-slate-800/50 border border-indigo-500/30 text-indigo-300 px-4 py-2 rounded-full text-xs font-mono tracking-tight w-fit">
              {getStatusIcon()}
              {agentStatus}
              <Loader2 className="w-3 h-3 animate-spin ml-2" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <form onSubmit={sendMessage} className="relative flex items-center">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. What is the MTU for an AWS Transit Gateway?"
          disabled={isLoading}
          className="w-full bg-slate-800 border border-slate-700 text-slate-100 rounded-xl px-4 py-4 pr-14 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50 transition-all"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="absolute right-2 p-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-50 disabled:hover:bg-indigo-600 transition-colors"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>
    </div>
  );
}