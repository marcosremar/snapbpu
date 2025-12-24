import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { marked } from 'marked';
import mermaid from 'mermaid';

// Import Dumont UI components
// Layout removed - now using AppLayout from App.jsx
import { Card, Button, Badge, Spinner } from '../components/tailadmin-ui';

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
});

// Configure mermaid
mermaid.initialize({ startOnLoad: false, theme: 'neutral' });

const Documentation = () => {
  const { docId } = useParams();
  const navigate = useNavigate();
  const [menu, setMenu] = useState([]);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeDoc, setActiveDoc] = useState(null);

  // Load menu on component mount
  useEffect(() => {
    loadMenu();
  }, []);

  // Load content when docId changes
  useEffect(() => {
    if (docId) {
      loadDoc(`${docId}.md`);
    } else if (menu.length > 0) {
      // Load first doc if no docId specified
      const firstDoc = findFirstDoc(menu);
      if (firstDoc) {
        // Check if we're in demo mode to use correct path
        const isDemo = window.location.pathname.startsWith('/demo');
        const basePath = isDemo ? '/demo-docs' : '/docs';
        navigate(`${basePath}/${firstDoc.replace('.md', '')}`, { replace: true });
      }
    }
  }, [docId, menu, navigate]);

  // Render mermaid diagrams after content loads
  useEffect(() => {
    if (content) {
      setTimeout(() => {
        mermaid.run();
      }, 100);
    }
  }, [content]);

  const loadMenu = async () => {
    try {
      const response = await fetch('/api/docs/menu');
      if (response.ok) {
        const data = await response.json();
        setMenu(data.menu);
      } else {
        throw new Error('API failed');
      }
    } catch (error) {
      console.warn('Error loading menu, using mock data:', error);
      // Mock Data for Style Audit
      setMenu([
        {
          name: 'Getting Started',
          type: 'dir',
          children: [
            { name: 'Introduction', type: 'file', id: '01_Introduction.md' },
            { name: 'Quick Start', type: 'file', id: '02_Quick_Start.md' }
          ]
        },
        {
          name: 'Features',
          type: 'dir',
          children: [
            { name: 'GPU Instances', type: 'file', id: '03_GPU_Instances.md' },
            { name: 'AI Wizard', type: 'file', id: '04_AI_Wizard.md' }
          ]
        }
      ]);
      // If no docId, we need to trigger loading of first doc manually or via effect
      // But effect depends on menu change, which happens here.
    }
  };

  const loadDoc = async (id) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/docs/content/${encodeURI(id)}`);
      if (response.ok) {
        const data = await response.json();
        const htmlContent = marked.parse(data.content);
        setContent(htmlContent);
        setActiveDoc(id);
      } else {
        throw new Error('Doc not found');
      }
    } catch (error) {
      console.warn('Error loading document, using mock content:', error);
      // Mock Content for Style Audit
      const mockMd = `# ${cleanName(id.replace('.md', ''))}\n\nWelcome to the Dumont Cloud documentation.\n\n## Overview\nThis is a mock content for style auditing purposes.\n\n- **Feature A**: Description\n- **Feature B**: Description\n\n\`\`\`javascript\nconsole.log("Hello Dumont");\n\`\`\``;
      setContent(marked.parse(mockMd));
      setActiveDoc(id);
    }
    setLoading(false);
  };

  const findFirstDoc = (items) => {
    for (const item of items) {
      if (item.type === 'file') return item.id;
      if (item.type === 'dir' && item.children) {
        const child = findFirstDoc(item.children);
        if (child) return child;
      }
    }
    return null;
  };

  const cleanName = (name) => {
    return name
      .replace(/^\d+_/, '')  // Remove leading numbers like "01_"
      .replace(/_/g, ' ')     // Replace underscores with spaces
      .trim();
  };

  const getSectionIcon = (name) => {
    const icons = {
      'Getting Started': '🚀',
      'User Guide': '📖',
      'Features': '⚡',
      'API': '🔌',
      'Engineering': '🛠️',
      'Operations': '⚙️',
      'Business': '💼',
      'Research': '🔬',
      'Sprints': '🏃',
      'Analise Mercado': '📊'
    };
    const cleanedName = cleanName(name);
    return icons[cleanedName] || '📁';
  };

  const renderMenuItem = (item) => {
    if (item.type === 'file') {
      const docPath = item.id.replace('.md', '');
      const isActive = activeDoc === item.id;

      return (
        <Button
          key={item.id}
          variant="ghost"
          size="sm"
          className={`w-full justify-start mb-1 px-3 ${isActive
            ? 'bg-brand-500/10 text-brand-400 border border-brand-500/10 font-medium'
            : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          onClick={() => navigate(`/docs/${docPath}`)}
        >
          {cleanName(item.name)}
        </Button>
      );
    } else if (item.type === 'dir') {
      return (
        <div key={item.name} className="mb-6">
          <div className="flex items-center gap-2 mb-3 px-2">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              {getSectionIcon(item.name)} {cleanName(item.name)}
            </span>
          </div>
          <div className="ml-2">
            {item.children.map(renderMenuItem)}
          </div>
        </div>
      );
    }
    return null;
  };

  const copyCurrentUrl = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url);
  };

  return (
      <div className="flex h-screen bg-gray-50 dark:bg-[#0a0d0a] text-gray-900 dark:text-white">
        {/* Mobile sidebar toggle */}
        <div className="md:hidden fixed top-4 left-4 z-50">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="bg-[#0f1210] border-gray-800 text-gray-300"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </Button>
        </div>

        {/* Sidebar */}
        <aside className={`fixed inset-y-0 left-0 z-40 w-64 bg-[#0f1210] border-r border-white/5 transform transition-transform duration-200 ease-in-out md:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
          <div className="flex flex-col h-full">
            {/* Header */}
            <div className="p-6 border-b border-white/5">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded flex items-center justify-center bg-brand-500/10 text-brand-400">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                  </svg>
                </div>
                <h1 className="text-lg font-bold text-white tracking-tight">Dumont Cloud</h1>
              </div>
              <p className="text-xs text-brand-500/80 mt-1 uppercase tracking-wide bg-brand-500/10 inline-block px-1.5 py-0.5 rounded border border-brand-500/10">Live Docs</p>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto p-4 space-y-1">
              {menu.map(renderMenuItem)}
            </nav>

            {/* Back to app button */}
            <div className="p-4 border-t border-white/5 bg-[#0a0d0a]/50">
              <Button
                variant="outline"
                size="sm"
                className="w-full bg-white/5 border-white/10 hover:bg-brand-500/10 hover:text-brand-400 text-gray-400 transition-all font-medium"
                onClick={() => navigate('/')}
              >
                ← Voltar para App
              </Button>
            </div>
          </div>
        </aside>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-30 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main content */}
        <main className="flex-1 md:ml-64 bg-[#0a0d0a] overflow-auto">
          <div className="max-w-5xl mx-auto px-6 py-8 md:px-12 md:py-16">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <Spinner className="text-brand-500" />
                <span className="ml-3 text-gray-400 animate-pulse">Carregando documentação...</span>
              </div>
            ) : (
              <div className="rounded-2xl border border-white/5 bg-[#0f1210] p-8 md:p-12 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-[300px] h-[300px] bg-brand-500/5 rounded-full blur-[100px] pointer-events-none" />

                <div
                  className="prose prose-invert prose-green max-w-none prose-headings:font-bold prose-headings:tracking-tight prose-a:text-brand-400 prose-code:text-brand-300 prose-code:bg-brand-900/20 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-[#050605] prose-pre:border prose-pre:border-white/10 prose-img:rounded-xl prose-blockquote:border-brand-500 prose-blockquote:bg-brand-900/10 prose-blockquote:py-2 prose-blockquote:pr-2"
                  dangerouslySetInnerHTML={{ __html: content }}
                />
              </div>
            )}

            {/* Copy URL button */}
            {activeDoc && (
              <div className="fixed bottom-8 right-8 z-50">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={copyCurrentUrl}
                  className="shadow-lg shadow-brand-900/20 bg-brand-500 hover:bg-brand-600 text-white border-0 transition-transform hover:scale-105 active:scale-95 rounded-full px-4 py-3"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copiar Link
                </Button>
              </div>
            )}

            {/* Footer */}
            <footer className="mt-20 pt-8 border-t border-gray-200 dark:border-white/5 text-center text-xs text-gray-500">
              <p>Live Documentation System • Dumont Cloud &copy; 2025</p>
            </footer>
          </div>
        </main>
      </div>
  );
};

export default Documentation;
