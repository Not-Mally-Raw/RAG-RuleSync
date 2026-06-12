import React, { useState, useEffect, useRef } from 'react';
import { 
  Upload, 
  Settings, 
  FileText, 
  Trash2, 
  ArrowRight, 
  CheckCircle, 
  AlertTriangle, 
  Cpu, 
  Download, 
  Plus, 
  Copy, 
  Sparkles,
  HelpCircle,
  FileSpreadsheet
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'formalize'
  const [serverStatus, setServerStatus] = useState('checking'); // 'checking' | 'online' | 'offline'
  
  // Tab 1: Upload states
  const [file, setFile] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [extractedRules, setExtractedRules] = useState([]);
  const [selectedRules, setSelectedRules] = useState(new Set());
  const fileInputRef = useRef(null);

  // Tab 2: Formalize Builder states
  const [ruleInput, setRuleInput] = useState('');
  const [processing, setProcessing] = useState(false);
  const [formalizedRules, setFormalizedRules] = useState([]);

  // Check server health
  useEffect(() => {
    const checkServer = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (response.ok) {
          setServerStatus('online');
        } else {
          setServerStatus('offline');
        }
      } catch (err) {
        setServerStatus('offline');
      }
    };
    checkServer();
    const interval = setInterval(checkServer, 10000);
    return () => clearInterval(interval);
  }, []);

  // Handle file drop
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile);
      } else {
        alert('Please drop a valid PDF file.');
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  // Upload PDF
  const triggerUpload = async () => {
    if (!file) return;
    setUploading(true);
    setExtractedRules([]);
    setSelectedRules(new Set());
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch(`${API_BASE_URL}/upload-document`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('API server returned an error');
      }
      
      const data = await response.json();
      setExtractedRules(data);
    } catch (err) {
      alert(`Error extracting document: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  // Toggle selection of individual rules
  const toggleRuleSelection = (index) => {
    const nextSelected = new Set(selectedRules);
    if (nextSelected.has(index)) {
      nextSelected.delete(index);
    } else {
      nextSelected.add(index);
    }
    setSelectedRules(nextSelected);
  };

  // Select/Deselect all rules
  const toggleSelectAll = () => {
    if (selectedRules.size === extractedRules.length) {
      setSelectedRules(new Set());
    } else {
      const allIdx = new Set(extractedRules.map((_, i) => i));
      setSelectedRules(allIdx);
    }
  };

  // Send extracted rules to formalize builder
  const sendToBuilder = () => {
    const indicesToSend = selectedRules.size > 0 
      ? Array.from(selectedRules) 
      : extractedRules.map((_, i) => i);
      
    const rulesToSend = indicesToSend.map(idx => extractedRules[idx]);
    
    if (rulesToSend.length === 0) return;
    
    const text = rulesToSend.map(r => r.resolved_rule_text || r.rule_text).join('\n');
    setRuleInput(text);
    setActiveTab('formalize');
  };

  // Run Formalize / Refinement Pipeline
  const runFormalization = async () => {
    const lines = ruleInput.split('\n').map(l => l.trim()).filter(l => l !== '');
    if (lines.length === 0) {
      alert('Please enter at least one rule sentence.');
      return;
    }
    
    setProcessing(true);
    setFormalizedRules([]);
    
    const payload = {
      rules: lines.map(line => ({
        rule_text: line
      }))
    };
    
    try {
      const response = await fetch(`${API_BASE_URL}/process-rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        throw new Error('API server returned an error');
      }
      
      const data = await response.json();
      setFormalizedRules(data);
    } catch (err) {
      alert(`Error formalizing rules: ${err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  // Download formalized output as CSV
  const downloadCSV = () => {
    if (formalizedRules.length === 0) return;
    
    const headers = ['RuleText', 'Status', 'DecisionCode', 'RuleCategory', 'Feature1', 'Feature2', 'Object1', 'Object2', 'ExpName', 'Operator', 'Recom'];
    
    const rows = formalizedRules.map(r => {
      const dfm = r.dfm_rule || {};
      return [
        `"${r.rule_text.replace(/"/g, '""')}"`,
        r.status || '',
        r.decision_code || '',
        r.rule_category || '',
        dfm.Feature1 || '',
        dfm.Feature2 || '',
        dfm.Object1 || '',
        dfm.Object2 || '',
        dfm.ExpName || '',
        dfm.Operator || '',
        dfm.Recom !== undefined ? dfm.Recom : ''
      ];
    });
    
    const csvContent = [
      headers.join(','),
      ...rows.map(e => e.join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'dfm_rules_compiled.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert('Copied DFM rule to clipboard!');
  };

  return (
    <div className="app-container">
      {/* Header Section */}
      <header className="app-header">
        <div className="brand-section">
          <Cpu className="brand-logo" size={32} />
          <div>
            <h1 className="brand-title">DFM Rule Extraction</h1>
          </div>
        </div>
        <div className="server-status">
          <span className={`status-dot ${serverStatus === 'online' ? 'online' : ''}`}></span>
          <span>
            API Status: {serverStatus === 'online' ? 'Online' : serverStatus === 'offline' ? 'Offline' : 'Checking...'}
          </span>
        </div>
      </header>

      {/* Tabs Switcher */}
      <div className="tabs-navigation">
        <button 
          className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          <Upload size={18} />
          Document Ingestion
        </button>
        <button 
          className={`tab-btn ${activeTab === 'formalize' ? 'active' : ''}`}
          onClick={() => setActiveTab('formalize')}
        >
          <Sparkles size={18} />
          DFM Formalization
        </button>
      </div>

      {/* View 1: Document Upload */}
      {activeTab === 'upload' && (
        <div className="view-grid">
          {/* Controls Panel */}
          <div className="glass-panel">
            <h3 className="panel-title">
              <FileText size={20} />
              PDF Upload
            </h3>
            <div 
              className={`upload-zone ${isDragOver ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="upload-icon-wrapper">
                <Upload size={28} />
              </div>
              <div>
                <p className="upload-text-main">Drag & drop spec PDF here</p>
                <p className="upload-text-sub">or click to browse files</p>
              </div>
              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleFileChange}
                accept="application/pdf"
                style={{ display: 'none' }}
              />
            </div>

            {file && (
              <div className="selected-file-card">
                <div className="file-info">
                  <FileSpreadsheet size={18} className="brand-logo" />
                  <span className="file-name" title={file.name}>{file.name}</span>
                </div>
                <button className="remove-file-btn" onClick={() => setFile(null)}>
                  <Trash2 size={16} />
                </button>
              </div>
            )}

            <button 
              className="btn btn-primary" 
              style={{ width: '100%', marginTop: '1.5rem' }}
              disabled={!file || uploading || serverStatus !== 'online'}
              onClick={triggerUpload}
            >
              {uploading ? (
                <>
                  <div className="spinner" style={{ width: '16px', height: '16px' }}></div>
                  Extracting Rules...
                </>
              ) : (
                <>
                  <Cpu size={18} />
                  Run Extraction
                </>
              )}
            </button>
          </div>

          {/* Results Panel */}
          <div className="glass-panel">
            {uploading ? (
              <div className="processing-overlay">
                <div className="spinner" style={{ width: '40px', height: '40px' }}></div>
                <p className="processing-text">Running Level-1 Parsing Pipeline</p>
                <p className="processing-sub">Chunking document, indexing vectors, and querying anchors...</p>
              </div>
            ) : extractedRules.length > 0 ? (
              <div>
                <div className="results-header-section">
                  <div>
                    <h3 className="panel-title" style={{ marginBottom: '0.2rem' }}>
                      Extracted Candidate Rules
                      <span className="count-badge">{extractedRules.length} found</span>
                    </h3>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      Select rules to send to the DFM mathematical formalizer
                    </p>
                  </div>
                  <div className="results-actions">
                    <button className="btn btn-secondary btn-icon-only" title="Toggle Select All" onClick={toggleSelectAll}>
                      <CheckCircle size={18} />
                    </button>
                    <button className="btn btn-primary" onClick={sendToBuilder}>
                      Send to Refinement
                      <ArrowRight size={16} />
                    </button>
                  </div>
                </div>

                <div className="rules-list">
                  {extractedRules.map((rule, idx) => {
                    const isSel = selectedRules.has(idx);
                    return (
                      <div 
                        key={idx} 
                        className={`rule-card ${isSel ? 'is-selected' : ''}`}
                        onClick={() => toggleRuleSelection(idx)}
                        style={{ cursor: 'pointer' }}
                      >
                        <div className="rule-card-header">
                          <span>Rule #{idx + 1}</span>
                          {rule.source_window_ids && (
                            <div className="window-tags">
                              {rule.source_window_ids.slice(0, 3).map((wId, wIdx) => (
                                <span key={wIdx} className="window-tag">{wId.split('_').slice(-2).join('_')}</span>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="rule-text-block">
                          {rule.rule_text !== rule.resolved_rule_text && (
                            <>
                              <div className="rule-text-label">Verbatim:</div>
                              <div className="rule-text-verbatim">{rule.rule_text}</div>
                            </>
                          )}
                          <div className="rule-text-label">Resolved Context:</div>
                          <div className="rule-text-resolved">{rule.resolved_rule_text || rule.rule_text}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <FileText size={48} className="empty-state-icon" />
                <div>
                  <h4 style={{ color: '#ffffff', marginBottom: '0.25rem' }}>No Data Extracted</h4>
                  <p style={{ fontSize: '0.9rem' }}>Upload a PDF specification guidelines sheet to run the rule miner.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* View 2: DFM Formalization */}
      {activeTab === 'formalize' && (
        <div className="view-grid">
          {/* Rules Input Panel */}
          <div className="glass-panel">
            <h3 className="panel-title">
              <Cpu size={20} />
              DFM Rule Input
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
              Paste or type your manufacturing rule sentence below. You can enter multiple rules by putting each on a new line.
            </p>

            <div style={{ marginBottom: '1rem' }}>
              <textarea 
                className="input-field"
                placeholder="Example: Wall thickness must be at least 1.5mm for injection molding."
                rows={10}
                style={{ resize: 'vertical', minHeight: '200px', lineHeight: '1.5' }}
                value={ruleInput}
                onChange={(e) => setRuleInput(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button 
                className="btn btn-secondary" 
                style={{ flex: 1 }}
                onClick={() => setRuleInput('')}
                disabled={!ruleInput.trim()}
              >
                Clear Input
              </button>
            </div>

            <button 
              className="btn btn-primary" 
              style={{ width: '100%', marginTop: '1rem' }}
              disabled={processing || !ruleInput.trim() || serverStatus !== 'online'}
              onClick={runFormalization}
            >
              {processing ? (
                <>
                  <div className="spinner" style={{ width: '16px', height: '16px' }}></div>
                  Processing...
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  Compile Constraints
                </>
              )}
            </button>
          </div>

          {/* Formalized Outputs Panel */}
          <div className="glass-panel">
            {processing ? (
              <div className="processing-overlay">
                <div className="spinner" style={{ width: '40px', height: '40px' }}></div>
                <p className="processing-text">Running Refinement Pipeline</p>
                <p className="processing-sub">Resolving schema keys, parsing equations, and normalising CAD namespaces...</p>
              </div>
            ) : formalizedRules.length > 0 ? (
              <div>
                <div className="results-header-section">
                  <div>
                    <h3 className="panel-title" style={{ marginBottom: '0.2rem' }}>
                      Formalized CAD Constraints
                      <span className="count-badge">{formalizedRules.length} compiled</span>
                    </h3>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      Strict math equations generated for target assembly checking modules
                    </p>
                  </div>
                  <div className="results-actions">
                    <button className="btn btn-secondary" onClick={downloadCSV}>
                      <Download size={16} />
                      Export CSV
                    </button>
                  </div>
                </div>

                <div className="formalized-grid">
                  {formalizedRules.map((rule, idx) => {
                    const status = rule.status ? rule.status.toLowerCase() : '';
                    let statusClass = 'success';
                    if (status === 'skipped') statusClass = 'skipped';
                    else if (status === 'deferred') statusClass = 'deferred';
                    else if (status.includes('needed') || status.includes('fail')) statusClass = 'error';

                    return (
                      <div key={idx} className={`formalized-card ${statusClass}`}>
                        <div className="formalized-row-header">
                          <span className="rule-category-tag">{rule.rule_category}</span>
                          <span className={`badge badge-${statusClass}`}>
                            {rule.status || 'Success'}
                          </span>
                        </div>
                        <div className="formalized-card-body">
                          <p style={{ fontSize: '0.95rem', fontWeight: '500', marginBottom: '0.75rem', color: '#ffffff' }}>
                            "{rule.rule_text}"
                          </p>
                          {rule.dfm_rule ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                              <pre className="json-block">
                                {JSON.stringify(rule.dfm_rule, null, 2)}
                              </pre>
                              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                                <button 
                                  className="btn btn-secondary" 
                                  style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}
                                  onClick={() => copyToClipboard(JSON.stringify(rule.dfm_rule))}
                                >
                                  <Copy size={12} />
                                  Copy JSON
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="no-logic-tag">
                              Status: {rule.decision_code || 'Skipped (Non-quantifiable constraint)'}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <Sparkles size={48} className="empty-state-icon" />
                <div>
                  <h4 style={{ color: '#ffffff', marginBottom: '0.25rem' }}>No Constraints Compiled</h4>
                  <p style={{ fontSize: '0.9rem' }}>Fill in rule descriptions on the left and run the compiler to view outputs.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
