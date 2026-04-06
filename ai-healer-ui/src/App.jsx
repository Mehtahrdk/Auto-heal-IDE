import React, { useState, useRef } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import Editor from '@monaco-editor/react';
import { FileCode, Play, TerminalSquare, UploadCloud, Key } from 'lucide-react';
import './App.css';

function App() {
  const [apiKey, setApiKey] = useState('');
  const [file, setFile] = useState(null);
  const [targetFile, setTargetFile] = useState('main.py');
  
  const [isHealing, setIsHealing] = useState(false);
  const [logs, setLogs] = useState([
    { type: 'info', text: 'System ready. Awaiting codebase...' }
  ]);
  const [editorContent, setEditorContent] = useState(
    '# WELCOME TO AUTO-HEAL IDE\n# 1. Provide your Gemini 2.5 Pro API Key\n# 2. Upload your broken Python .zip repository\n# 3. Specify the entry point file\n# 4. Click Initialize Agent'
  );

  const fileInputRef = useRef(null);

  const addLog = (type, text) => {
    const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
    setLogs(prev => [...prev, { timestamp, type, text }]);
  };

  const handleFileChange = (e) => {
    if (e.target.files[0]) {
      setFile(e.target.files[0]);
      addLog('info', `File mounted: ${e.target.files[0].name}`);
    }
  };

  const triggerHealing = async () => {
    if (!apiKey) return alert("API Key is required.");
    if (!file) return alert("Codebase ZIP is required.");

    setIsHealing(true);
    setLogs([]);
    addLog('info', 'Initializing Agentic Environment...');
    addLog('info', `Targeting file: ${targetFile}`);
    setEditorContent('# Agent is analyzing the codebase...\n# Please wait.');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_file', targetFile);
    formData.append('api_key', apiKey);

    try {
      addLog('info', 'Executing API request to Agent server...');
      addLog('info', '[Standby] Depending on complexity, this may take 1-2 minutes.');
      
      const response = await fetch('http://127.0.0.1:8000/heal', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (data.status === 'success') {
        addLog('success', 'Codebase successfully repaired.');
        // Display the agent's markdown response in the Monaco Editor
        setEditorContent(`"""\nAGENT REPORT\nSession ID: ${data.session_id}\n"""\n\n${data.final_message[0].text}`);
      } else {
        addLog('error', `Agent Error: ${data.final_message[0].text}`);
        setEditorContent(`# ERROR REPORT\n\n${data.final_message[0].text}`);
      }

    } catch (error) {
      addLog('error', 'Critical System Failure: Cannot connect to Backend Server.');
      setEditorContent('# Connection Error.\n# Ensure uvicorn server is running on port 8000.');
    } finally {
      setIsHealing(false);
    }
  };

  return (
    <div className="ide-container">
      {/* Top Bar */}
      <div className="ide-header">
        <div className="ide-header-logo">
          <TerminalSquare size={16} color="#007acc" />
          <span>Auto-Heal IDE</span>
        </div>
      </div>

      <div className="ide-body">
        <PanelGroup direction="horizontal">
          
          {/* LEFT SIDEBAR */}
          <Panel defaultSize={20} minSize={15} maxSize={30}>
            <div className="sidebar">
              <div className="section-title">Configuration</div>

              <div className="input-group">
                <label>Gemini API Key</label>
                <div style={{ position: 'relative' }}>
                  <Key size={14} style={{ position: 'absolute', top: '9px', left: '8px', color: '#858585' }} />
                  <input
                    type="password"
                    className="ide-input"
                    style={{ width: '100%', paddingLeft: '28px' }}
                    placeholder="AIzaSy..."
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    disabled={isHealing}
                  />
                </div>
              </div>

              <div className="section-title" style={{ marginTop: '10px' }}>Workspace</div>

              <div className="drop-zone" onClick={() => fileInputRef.current.click()}>
                <UploadCloud size={24} color={file ? "#89d185" : "#858585"} />
                <span>{file ? file.name : "Select Codebase .zip"}</span>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  hidden
                  accept=".zip"
                  disabled={isHealing}
                />
              </div>

              <div className="input-group">
                <label>Entry Point (e.g., main.py)</label>
                <div style={{ position: 'relative' }}>
                  <FileCode size={14} style={{ position: 'absolute', top: '9px', left: '8px', color: '#858585' }} />
                  <input
                    type="text"
                    className="ide-input"
                    style={{ width: '100%', paddingLeft: '28px' }}
                    value={targetFile}
                    onChange={(e) => setTargetFile(e.target.value)}
                    disabled={isHealing}
                  />
                </div>
              </div>

              <div style={{ flexGrow: 1 }} />

              <button 
                className="btn-primary" 
                onClick={triggerHealing}
                disabled={isHealing || !file || !apiKey}
              >
                {isHealing ? <span className="pulse-cursor" style={{ background: 'white' }} /> : <Play size={16} />}
                {isHealing ? 'PROCESSING...' : 'INITIALIZE AGENT'}
              </button>
            </div>
          </Panel>

          <PanelResizeHandle className="resize-handle-vertical" />

          {/* MAIN WORKSPACE (EDITOR + TERMINAL) */}
          <Panel defaultSize={80}>
            <PanelGroup direction="vertical">
              
              {/* TOP: MONACO EDITOR */}
              <Panel defaultSize={70} minSize={30}>
                <div className="editor-container">
                  <Editor
                    height="100%"
                    defaultLanguage="python"
                    theme="vs-dark"
                    value={editorContent}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 14,
                      wordWrap: 'on',
                      readOnly: true,
                      padding: { top: 20 }
                    }}
                  />
                </div>
              </Panel>

              <PanelResizeHandle className="resize-handle-horizontal" />

              {/* BOTTOM: TERMINAL */}
              <Panel defaultSize={30} minSize={15}>
                <div className="terminal-container">
                  <div className="terminal-header">
                    OUTPUT CONSOLE
                  </div>
                  <div className="terminal-body">
                    {logs.map((log, index) => (
                      <div key={index} className="log-line">
                        <span className="log-timestamp">[{log.timestamp}]</span>
                        <span className={`log-${log.type}`}>{log.text}</span>
                      </div>
                    ))}
                    {isHealing && (
                      <div className="log-line">
                        <span className="log-timestamp">[{new Date().toLocaleTimeString('en-US', { hour12: false })}]</span>
                        <span className="log-info">Awaiting agent response <span className="pulse-cursor"></span></span>
                      </div>
                    )}
                  </div>
                </div>
              </Panel>

            </PanelGroup>
          </Panel>

        </PanelGroup>
      </div>
    </div>
  );
}

export default App;