import { useState } from 'react';
import { Users, Activity, ShieldAlert, CheckCircle, BarChart3, Lock } from 'lucide-react';
import React from 'react'; // Added import for React

export const AdminDashboard: React.FC = () => {
    const API_URL = (window as any).config?.API_URL || 'http://localhost:3000/api';
    const [activeView, setActiveView] = useState<'overview' | 'users' | 'audit'>('overview');
    const [auditLogs, setAuditLogs] = useState<any[]>([]);

    // Fetch Audit Logs when view changes to 'audit'
    if (activeView === 'audit' && auditLogs.length === 0) {
        fetch(`${API_URL}/audit`)
            .then(res => res.json())
            .then(data => setAuditLogs(Array.isArray(data) ? data : []))
            .catch(err => console.error("Failed to fetch audit logs:", err));
    }

    return (
        <div className="flex h-screen bg-slate-100 font-sans">
            {/* Sidebar */}
            <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col">
                <div className="p-6 border-b border-slate-800">
                    <h2 className="text-white font-bold flex items-center gap-2">
                        <Lock className="w-5 h-5 text-red-500" /> Admin Panel
                    </h2>
                    <p className="text-xs mt-1 text-slate-500">Enterprise Governance</p>
                </div>
                <nav className="flex-1 p-4 space-y-2">
                    <button
                        onClick={() => setActiveView('overview')}
                        className={`w-full text-left px-4 py-3 rounded-lg flex items-center gap-3 transition ${activeView === 'overview' ? 'bg-slate-800 text-white' : 'hover:bg-slate-800/50'}`}
                    >
                        <Activity className="w-5 h-5" /> System Health
                    </button>
                    <button
                        onClick={() => setActiveView('users')}
                        className={`w-full text-left px-4 py-3 rounded-lg flex items-center gap-3 transition ${activeView === 'users' ? 'bg-slate-800 text-white' : 'hover:bg-slate-800/50'}`}
                    >
                        <Users className="w-5 h-5" /> User Management
                    </button>
                    <button
                        onClick={() => setActiveView('audit')}
                        className={`w-full text-left px-4 py-3 rounded-lg flex items-center gap-3 transition ${activeView === 'audit' ? 'bg-slate-800 text-white' : 'hover:bg-slate-800/50'}`}
                    >
                        <ShieldAlert className="w-5 h-5" /> Compliance Logs
                    </button>
                </nav>
                <div className="p-4 border-t border-slate-800">
                    <p className="text-xs text-slate-500">v2.0.0-ENT</p>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto p-8">
                {activeView === 'overview' && (
                    <div className="space-y-6">
                        <h1 className="text-2xl font-bold text-slate-800">System Overview</h1>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-slate-500 font-medium">Active Pipelines</h3>
                                    <BarChart3 className="w-5 h-5 text-blue-500" />
                                </div>
                                <p className="text-3xl font-bold text-slate-900">12</p>
                                <p className="text-sm text-green-600 mt-1 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> All operational</p>
                            </div>
                            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-slate-500 font-medium">Estimated Cost (MTD)</h3>
                                    <span className="text-xs bg-slate-100 px-2 py-1 rounded">USD</span>
                                </div>
                                <p className="text-3xl font-bold text-slate-900">$45.20</p>
                                <p className="text-sm text-slate-400 mt-1">Bedrock Tokens usage</p>
                            </div>
                            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-slate-500 font-medium">Security Alerts</h3>
                                    <ShieldAlert className="w-5 h-5 text-red-500" />
                                </div>
                                <p className="text-3xl font-bold text-slate-900">0</p>
                                <p className="text-sm text-green-600 mt-1">System secure</p>
                            </div>
                        </div>
                    </div>
                )}

                {activeView === 'users' && (
                    <div className="space-y-6">
                        <div className="flex justify-between items-center">
                            <h1 className="text-2xl font-bold text-slate-800">User Management (RBAC)</h1>
                            <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">Invite User</button>
                        </div>

                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                            <table className="w-full text-left">
                                <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500">
                                    <tr>
                                        <th className="px-6 py-4">User</th>
                                        <th className="px-6 py-4">Role</th>
                                        <th className="px-6 py-4">Last Active</th>
                                        <th className="px-6 py-4">Status</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    <tr>
                                        <td className="px-6 py-4 font-medium">alice@firm.com</td>
                                        <td className="px-6 py-4"><span className="bg-purple-100 text-purple-700 px-2 py-1 rounded-full text-xs font-bold">Partner</span></td>
                                        <td className="px-6 py-4 text-slate-500">2 mins ago</td>
                                        <td className="px-6 py-4 text-green-600 text-sm">Active</td>
                                    </tr>
                                    <tr>
                                        <td className="px-6 py-4 font-medium">bob@firm.com</td>
                                        <td className="px-6 py-4"><span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-xs font-bold">Associate</span></td>
                                        <td className="px-6 py-4 text-slate-500">2 days ago</td>
                                        <td className="px-6 py-4 text-green-600 text-sm">Active</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
                {activeView === 'audit' && (
                    <div className="space-y-6">
                        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                            <ShieldAlert className="w-6 h-6 text-slate-800" /> Compliance Ledger
                        </h1>
                        <div className="bg-amber-50 border border-amber-200 p-4 rounded-lg text-sm text-amber-800 mb-4">
                            <strong>Immutable Record:</strong> All actions below are cryptographically signed and archived to S3 Glacier WORM storage.
                        </div>

                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                            <table className="w-full text-left font-mono text-sm">
                                <thead className="bg-slate-900 text-slate-200">
                                    <tr>
                                        <th className="px-6 py-3">Timestamp (UTC)</th>
                                        <th className="px-6 py-3">Actor</th>
                                        <th className="px-6 py-3">Action</th>
                                        <th className="px-6 py-3">Resource</th>
                                        <th className="px-6 py-3">Hash</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {auditLogs.map((log: any, i) => (
                                        <tr key={i} className="hover:bg-slate-50">
                                            <td className="px-6 py-3 text-slate-500">{new Date(log.timestamp).toLocaleString()}</td>
                                            <td className="px-6 py-3 font-bold text-blue-600">{log.user_id}</td>
                                            <td className="px-6 py-3">{log.action}</td>
                                            <td className="px-6 py-3 truncate max-w-xs" title={log.details || log.resource}>{log.details || log.resource}</td>
                                            <td className="px-6 py-3 text-xs text-slate-400 font-mono">{log.hash?.substring(0, 10)}...</td>
                                        </tr>
                                    ))}
                                    {auditLogs.length === 0 && (
                                        <tr>
                                            <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                                                No audit logs found.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
