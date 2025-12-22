import React, { useState } from 'react';
import { Upload, FileText, Send, Search, Scale, AlertCircle } from 'lucide-react';
import { AdminDashboard } from './admin/AdminDashboard';
import { v4 as uuidv4 } from 'uuid';

// Extend global Window interface
declare global {
    interface Window {
        config?: {
            API_URL?: string;
        };
    }
}

function App() {
    // Read from window.config (injected at runtime) or fallback to local assumption
    const API_URL = window.config?.API_URL || 'http://localhost:3000/api';
    const [activeTab, setActiveTab] = useState<'dashboard' | 'chat' | 'admin'>('dashboard');
    const [query, setQuery] = useState('');
    const [chatHistory, setChatHistory] = useState<{ role: 'user' | 'ai', content: string, sources?: any[] }[]>([
        { role: 'ai', content: 'Hello. I am CaseChat. I have analyzed available documents. What would you like to know about the current evidence?' }
    ]);
    const [documents, setDocuments] = useState<any[]>([]);
    const [selectedDoc, setSelectedDoc] = useState('');
    const [sessionId, setSessionId] = useState('');

    const [isUploading, setIsUploading] = useState(false);

    const fetchDocuments = () => {
        fetch(`${API_URL}/documents`)
            .then(res => res.json())
            .then(data => setDocuments(Array.isArray(data) ? data : []))
            .catch(err => console.error("Failed to fetch docs:", err));
    };

    React.useEffect(() => {
        // Initialize Session ID
        let storedSession = localStorage.getItem('casechat_session_id');
        if (!storedSession) {
            storedSession = uuidv4();
            localStorage.setItem('casechat_session_id', storedSession);
        }
        setSessionId(storedSession);

        // Initial Fetch
        fetchDocuments();
    }, []);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        try {
            // 1. Get Presigned URL
            const contentType = file.type || 'application/octet-stream';
            const res = await fetch(`${API_URL}/upload-url?filename=${encodeURIComponent(file.name)}&contentType=${encodeURIComponent(contentType)}`);
            const { uploadUrl } = await res.json();

            // 2. Upload to S3
            await fetch(uploadUrl, {
                method: 'PUT',
                body: file,
                headers: { 'Content-Type': contentType }
            });

            // 3. Refresh Docs & Reset UI
            // wait a sec for S3 event consistentcy if needed, though instant is usually fine
            setTimeout(() => {
                fetchDocuments();
                setIsUploading(false);
                alert(`Success! File "${file.name}" uploaded. Processing started.`);
            }, 1000);

        } catch (err) {
            console.error(err);
            alert('Upload failed. See console.');
            setIsUploading(false);
        }
    };

    const [activeCitation, setActiveCitation] = useState<any | null>(null);

    const handleSend = async () => {
        if (!query) return;

        // Add User Message
        const newHistory = [...chatHistory, { role: 'user', content: query } as const];
        setChatHistory(newHistory);
        setQuery('');

        // Temporary Loading State
        setChatHistory(prev => [...prev, { role: 'ai', content: 'Thinking...' } as const]);

        try {
            const res = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, docId: selectedDoc || null, sessionId })
            });
            const data = await res.json();

            // Replace Loading with Real Answer
            setChatHistory(prev => [
                ...prev.slice(0, -1), // Remove "Thinking..."
                {
                    role: 'ai',
                    content: data.answer || "I couldn't find an answer.",
                    sources: data.sources || []
                } as any
            ]);
        } catch (err) {
            console.error(err);
            setChatHistory(prev => [
                ...prev.slice(0, -1),
                { role: 'ai', content: "Error connecting to research assistant." } as any
            ]);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
            {/* Header */}
            <header className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between shadow-lg">
                <div className="flex items-center gap-3">
                    <Scale className="w-8 h-8 text-blue-400" />
                    <h1 className="text-xl font-bold tracking-tight">LexGuard <span className="text-slate-400 font-normal">| Enterprise Risk Guardian</span></h1>
                </div>
                <nav className="flex gap-4 text-sm font-medium">
                    <button
                        onClick={() => setActiveTab('dashboard')}
                        className={`px-3 py-2 rounded-md transition ${activeTab === 'dashboard' ? 'bg-slate-800 text-blue-400' : 'hover:text-blue-300'}`}
                    >
                        Dashboard
                    </button>
                    <button
                        onClick={() => setActiveTab('chat')}
                        className={`px-3 py-2 rounded-md transition ${activeTab === 'chat' ? 'bg-slate-800 text-blue-400' : 'hover:text-blue-300'}`}
                    >
                        Research Assistant
                    </button>
                    <button
                        onClick={() => setActiveTab('admin')}
                        className={`px-3 py-2 rounded-md transition border border-slate-700 ${activeTab === 'admin' ? 'bg-red-900/20 text-red-400 border-red-900' : 'hover:text-red-300 hover:border-red-900'}`}
                    >
                        Admin Panel
                    </button>
                </nav>
            </header>

            {/* Main Content */}
            <main className="flex-1 max-w-7xl w-full mx-auto p-6">

                {activeTab === 'admin' && <div className="h-[85vh] rounded-xl overflow-hidden border border-slate-200 shadow-xl"><AdminDashboard /></div>}

                {activeTab === 'dashboard' && (
                    <div className="space-y-8">
                        {/* Upload Zone */}
                        <section className="bg-white p-8 rounded-xl shadow-sm border border-slate-200 border-dashed border-2 hover:border-blue-400 transition cursor-pointer group relative overflow-hidden">
                            {isUploading && (
                                <div className="absolute inset-0 bg-white/90 z-10 flex flex-col items-center justify-center backdrop-blur-sm">
                                    <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-2"></div>
                                    <p className="text-sm font-semibold text-blue-600 animate-pulse">Uploading Evidence...</p>
                                </div>
                            )}
                            <label className="flex flex-col items-center justify-center gap-4 cursor-pointer">
                                <div className="p-4 bg-slate-100 rounded-full group-hover:bg-blue-50 transition">
                                    <Upload className="w-8 h-8 text-slate-500 group-hover:text-blue-500" />
                                </div>
                                <div className="text-center">
                                    <p className="text-lg font-medium text-slate-700">Drop evidence files here</p>
                                    <p className="text-sm text-slate-500">PDF, DOCX supported. Max 50MB.</p>
                                </div>
                                <input type="file" className="hidden" onChange={handleUpload} disabled={isUploading} />
                            </label>
                        </section>

                        {/* Document List */}
                        <section>
                            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <FileText className="w-5 h-5" /> Case Evidence
                            </h2>
                            <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
                                <table className="w-full text-left">
                                    <thead className="bg-slate-50 border-b border-slate-200 text-xs uppercase text-slate-500 font-semibold">
                                        <tr>
                                            <th className="px-6 py-4">Document Name</th>
                                            <th className="px-6 py-4">Date Uploaded</th>
                                            <th className="px-6 py-4">Risk Level</th>
                                            <th className="px-6 py-4">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100">
                                        {documents.map((doc: any) => (
                                            <tr key={doc.id} className="hover:bg-slate-50 transition group">
                                                <td className="px-6 py-4 font-medium text-slate-700 flex items-center gap-3">
                                                    <div className="w-8 h-8 bg-red-100 rounded text-red-500 flex items-center justify-center text-xs font-bold">PDF</div>
                                                    {doc.name}
                                                </td>
                                                <td className="px-6 py-4 text-slate-500">{new Date(doc.date).toLocaleDateString()}</td>
                                                <td className="px-6 py-4 relative">
                                                    <div className="flex items-center gap-2 cursor-help">
                                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${doc.risk_score === 'High' ? 'bg-red-100 text-red-800 border-red-200' :
                                                            doc.risk_score === 'Medium' ? 'bg-amber-100 text-amber-800 border-amber-200' :
                                                                'bg-green-100 text-green-800 border-green-200'
                                                            }`}>
                                                            {doc.risk_score === 'High' && <AlertCircle className="w-3 h-3 mr-1" />}
                                                            {doc.risk_score || 'Low'} Risk
                                                        </span>

                                                        {/* Tooltip for Flags */}
                                                        {doc.risk_flags && doc.risk_flags.length > 0 && (
                                                            <div className="absolute left-6 bottom-full mb-2 w-64 bg-slate-800 text-white text-xs rounded-lg p-3 shadow-xl opacity-0 group-hover:opacity-100 transition pointer-events-none z-50">
                                                                <p className="font-bold mb-1 border-b border-slate-600 pb-1">Detected Issues:</p>
                                                                <ul className="list-disc pl-4 space-y-1">
                                                                    {doc.risk_flags.map((flag: string, i: number) => (
                                                                        <li key={i}>{flag}</li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600`}>
                                                        {doc.status || 'Indexed'}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                        {documents.length === 0 && (
                                            <tr>
                                                <td colSpan={4} className="px-6 py-8 text-center text-slate-500">
                                                    No documents found. Upload evidence to begin scan.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    </div>
                )}

                {activeTab === 'chat' && (
                    <div className="h-[80vh] flex gap-6">
                        {/* Chat Area */}
                        <div className="flex-1 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
                            <div className="flex-1 p-6 overflow-y-auto space-y-6 bg-slate-50/50">
                                {chatHistory.map((msg: any, i) => (
                                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[80%] rounded-2xl p-4 shadow-sm ${msg.role === 'user'
                                            ? 'bg-blue-600 text-white rounded-br-none'
                                            : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none'
                                            }`}>
                                            <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>

                                            {/* Smart Citations UI */}
                                            {msg.sources && msg.sources.length > 0 && (
                                                <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap gap-2 items-center">
                                                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-1">Citations:</span>
                                                    {msg.sources.map((source: any, idx: number) => (
                                                        <button
                                                            key={idx}
                                                            onMouseEnter={() => setActiveCitation(source)}
                                                            className="flex items-center justify-center w-6 h-6 bg-blue-50 text-blue-600 text-xs font-bold rounded hover:bg-blue-100 transition border border-blue-100 shadow-sm"
                                                            title={`Source: ${source.metadata.source} (Score: ${Math.round(source.score * 100)}%)`}
                                                        >
                                                            {idx + 1}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <div className="p-4 bg-white border-t border-slate-200">
                                <div className="flex gap-2">
                                    <select
                                        className="px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition max-w-[200px] text-sm text-slate-600"
                                        value={selectedDoc}
                                        onChange={e => setSelectedDoc(e.target.value)}
                                    >
                                        <option value="">All Documents</option>
                                        {documents.map(doc => (
                                            <option key={doc.id} value={doc.id}>{doc.name}</option>
                                        ))}
                                    </select>
                                    <input
                                        type="text"
                                        value={query}
                                        onChange={e => setQuery(e.target.value)}
                                        onKeyDown={e => e.key === 'Enter' && handleSend()}
                                        placeholder="Ask about the evidence..."
                                        className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                                    />
                                    <button
                                        onClick={handleSend}
                                        className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition flex items-center gap-2"
                                    >
                                        <Send className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Sidebar Context */}
                        <div className="w-80 bg-white rounded-xl shadow-sm border border-slate-200 p-6 hidden lg:block overflow-y-auto">
                            <h3 className="text-sm font-bold uppercase text-slate-400 mb-4 flex items-center gap-2">
                                <AlertCircle className="w-4 h-4" /> Live Citations
                            </h3>
                            {activeCitation ? (
                                <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                                    <div className="p-4 bg-blue-50/50 rounded-lg border border-blue-100 text-sm">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="font-semibold text-blue-700">Source Match</span>
                                            <span className="text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded-full">
                                                {Math.round(activeCitation.score * 100)}% Relevancy
                                            </span>
                                        </div>
                                        <p className="text-slate-600 leading-relaxed font-mono text-xs p-2 bg-white rounded border border-blue-100">
                                            "{activeCitation.metadata.text}"
                                        </p>
                                        <p className="mt-2 text-xs text-slate-400 font-medium">
                                            Source: {activeCitation.metadata.source || 'Unknown Document'}
                                        </p>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center py-10 text-slate-400">
                                    <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p className="text-sm">Hover over a citation<br />to see the source text.</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}

export default App;
