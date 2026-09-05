import { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Copy,
  Cpu,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  Moon,
  Sparkles,
  Sun,
  Trash2,
  Upload,
} from 'lucide-react';

// When running through Vite dev server, use relative URLs so the proxy forwards to the backend.
// For production or standalone testing, set VITE_API_BASE_URL in your .env file.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';


const DOMAIN_OPTIONS = [
  { label: 'Auto detect', value: '' },
  { label: 'SheetMetal', value: 'Sheetmetal' },
  { label: 'Drilling', value: 'Drilling' },
  { label: 'Assembly', value: 'Assembly' },
  { label: 'Injection Molding', value: 'Injection Molding' },
  { label: 'Milling', value: 'Milling' },
  { label: 'Turning', value: 'Turning' },
  { label: 'Tubing', value: 'Tubing' },
  { label: 'Die Casting', value: 'Die Casting' },
  { label: 'Additive Manufacturing', value: 'Additive Manufacturing' },
  { label: 'Sheetmetal Forming', value: 'Sheetmetal Forming' },
  { label: 'General', value: 'General' },
];

const SAMPLE_RULES = [
  'Distance between bridges should be at least 4.5 times sheet thickness',
  'If a hole is blind, total depth to diameter ratio is 2.0; otherwise it is 4.0',
  'Material must be one of Steel, Aluminium, or Brass',
];

function toJsonText(value) {
  return JSON.stringify(value, null, 2);
}

function downloadBlob(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function getStatusClass(status = '') {
  const normalized = status.toLowerCase();
  if (normalized.includes('success')) return 'success';
  if (normalized.includes('skipped')) return 'skipped';
  if (normalized.includes('deferred')) return 'deferred';
  if (normalized.includes('review') || normalized.includes('fail')) return 'error';
  return 'deferred';
}

function App() {
  const [activeTab, setActiveTab] = useState('formalize');
  const [serverStatus, setServerStatus] = useState('checking');
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');

  const [file, setFile] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [extractedRules, setExtractedRules] = useState([]);
  const [selectedRules, setSelectedRules] = useState(new Set());
  const fileInputRef = useRef(null);

  const [ruleInput, setRuleInput] = useState(SAMPLE_RULES[0]);
  const [domainOverride, setDomainOverride] = useState('');
  const [formalizerMode, setFormalizerMode] = useState('taxonomy'); // 'taxonomy' or 'legacy'
  const [processing, setProcessing] = useState(false);
  const [formalizedRules, setFormalizedRules] = useState([]);
  const [requestError, setRequestError] = useState('');

  useEffect(() => {
    const checkServer = async () => {
      try {
        // Health check always hits the backend root directly.
        // Falls back to http://localhost:8000 if VITE_API_BASE_URL is not set.
        const healthUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${healthUrl}/`);
        setServerStatus(response.ok ? 'online' : 'offline');
      } catch {
        setServerStatus('offline');
      }
    };

    checkServer();
    const interval = setInterval(checkServer, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const setRulesFromLines = (lines) => {
    setRuleInput(lines.join('\n'));
    setFormalizedRules([]);
    setRequestError('');
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragOver(false);
    const droppedFile = event.dataTransfer.files?.[0];
    if (!droppedFile) return;
    if (droppedFile.type !== 'application/pdf') {
      setRequestError('Please drop a PDF file.');
      return;
    }
    setFile(droppedFile);
  };

  const triggerUpload = async () => {
    if (!file) return;

    setUploading(true);
    setRequestError('');
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
        const detail = await response.text();
        throw new Error(detail || 'Document extraction failed.');
      }

      setExtractedRules(await response.json());
    } catch (error) {
      setRequestError(error.message);
    } finally {
      setUploading(false);
    }
  };

  const toggleRuleSelection = (index) => {
    setSelectedRules((previous) => {
      const next = new Set(previous);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedRules.size === extractedRules.length) {
      setSelectedRules(new Set());
      return;
    }
    setSelectedRules(new Set(extractedRules.map((_, index) => index)));
  };

  const sendToBuilder = () => {
    const indexes = selectedRules.size > 0 ? Array.from(selectedRules) : extractedRules.map((_, index) => index);
    const rawTexts = indexes
      .map((index) => extractedRules[index])
      .map((rule) => rule.resolved_rule_text || rule.rule_text)
      .filter(Boolean);

    if (rawTexts.length === 0) return;

    // Split any multi-line or bulleted items so each rule has its own clean line in the compiler
    const cleanLines = rawTexts.flatMap((text) =>
      text
        .replace(/\r\n/g, '\n')
        .split('\n')
        .map((l) => l.replace(/^\s*(?:[-â€¢*â€“â€”]|\(?\d+[.)]|\([a-zA-Z]\))\s*/, '').trim())
        .filter((l) => l.length > 5)
    );

    setRulesFromLines(cleanLines.length > 0 ? cleanLines : rawTexts);
    setActiveTab('formalize');
  };

  const buildPayload = () => {
    const lines = ruleInput
      .replace(/\r\n/g, '\n')
      .split('\n')
      .map((line) => line.replace(/^\s*(?:[-â€¢*â€“â€”]|\(?\d+[.)]|\([a-zA-Z]\))\s*/, '').trim())
      .filter(Boolean);

    return {
      rules: lines.map((line) => ({
        rule_text: line,
        ...(domainOverride ? { rule_type: domainOverride } : {}),
      })),
    };
  };

  const runFormalization = async () => {
    const payload = buildPayload();
    if (payload.rules.length === 0) {
      setRequestError('Enter at least one rule sentence.');
      return;
    }

    const endpoint = formalizerMode === 'taxonomy' ? '/process-rules-taxonomy' : '/process-rules';

    setProcessing(true);
    setFormalizedRules([]);
    setRequestError('');

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `${endpoint} returned ${response.status}`);
      }

      setFormalizedRules(await response.json());
    } catch (error) {
      setRequestError(error.message);
    } finally {
      setProcessing(false);
    }
  };

  const copyToClipboard = async (value) => {
    await navigator.clipboard.writeText(typeof value === 'string' ? value : toJsonText(value));
  };

  const exportResults = () => {
    if (formalizedRules.length === 0) return;
    const name = formalizerMode === 'taxonomy' ? 'taxonomy_formalization_results.json' : 'legacy_formalization_results.json';
    downloadBlob(name, toJsonText(formalizedRules), 'application/json;charset=utf-8');
  };

  const renderLegacyOutput = (result, index) => {
    const statusClass = getStatusClass(result.status);

    return (
      <div key={`${result.rule_text}-${index}`} className={`formalized-card ${statusClass}`}>
        <div className="formalized-row-header">
          <span className="rule-category-tag">{result.rule_category || 'Unknown category'}</span>
          <span className={`badge badge-${statusClass}`}>{result.status || 'Success'}</span>
        </div>
        <p className="rule-preview">"{result.rule_text}"</p>
        {result.dfm_rule ? (
          <>
            <pre className="json-block">{toJsonText(result.dfm_rule)}</pre>
            <button className="btn btn-secondary compact-btn" onClick={() => copyToClipboard(result.dfm_rule)} style={{ marginTop: '0.75rem' }}>
              <Copy size={13} />
              Copy JSON
            </button>
          </>
        ) : (
          <div className="no-logic-tag">Status: {result.decision_code || 'No structured rule returned'}</div>
        )}
      </div>
    );
  };

  const renderTaxonomyOutput = (result, index) => {
    const statusClass = getStatusClass(result.status);

    return (
      <div key={`${result.rule_text}-${index}`} className={`formalized-card ${statusClass}`}>
        <div className="formalized-row-header">
          <span className="rule-category-tag">{result.domain || 'Auto detected'}</span>
          <span className={`badge badge-${statusClass}`}>{result.status || 'Success'}</span>
        </div>
        
        <p className="rule-preview">"{result.rule_text}"</p>

        <div className="metadata-grid">
          <div>
            <span>Bucket</span>
            <strong>{result.bucket || 'N/A'}</strong>
          </div>
          <div>
            <span>Domain</span>
            <strong>{result.domain || 'N/A'}</strong>
          </div>
          <div>
            <span>Decision Code</span>
            <strong>{result.decision_code || 'N/A'}</strong>
          </div>
        </div>

        {result.validation_errors && result.validation_errors.length > 0 && (
          <div className="error-list">
            {result.validation_errors.map((error, errIdx) => (
              <div key={`err-${errIdx}`} className="error-item">
                <AlertTriangle size={18} style={{ marginTop: '0.1rem' }} />
                <div>
                  <strong style={{ fontSize: '0.85rem' }}>[{error.code}]</strong>
                  <p>{error.message}</p>
                  {error.suggestion && <small>Suggestion: {error.suggestion}</small>}
                </div>
              </div>
            ))}
          </div>
        )}

        {result.taxonomy_rules && result.taxonomy_rules.length > 0 ? (
          <>
            <pre className="json-block">{toJsonText(result.taxonomy_rules)}</pre>
            <button className="btn btn-secondary compact-btn" onClick={() => copyToClipboard(result.taxonomy_rules)} style={{ marginTop: '0.75rem' }}>
              <Copy size={13} />
              Copy JSON
            </button>
          </>
        ) : (
          <div className="no-logic-tag" style={{ color: 'var(--color-danger)' }}>
            Pipeline status: {result.decision_code || 'Compilation failed'}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="brand-section">
          <Cpu className="brand-logo" size={32} />
          <div>
            <h1 className="brand-title">RAG-RuleSync</h1>
            <p className="brand-subtitle">DFM Rule Compiler</p>
          </div>
        </div>

        <div className="header-actions">
          <div className="server-status">
            <span className={`status-dot ${serverStatus === 'online' ? 'online' : ''}`} />
            <span>
              API Status: {serverStatus === 'online' ? 'Online' : serverStatus === 'offline' ? 'Offline' : 'Checking'}
            </span>
          </div>
          <button
            className="btn btn-secondary btn-icon-only"
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
        </div>
      </header>

      <div className="tabs-navigation">
        <button className={`tab-btn ${activeTab === 'formalize' ? 'active' : ''}`} onClick={() => setActiveTab('formalize')}>
          <Sparkles size={18} />
          Rule Compiler
        </button>
        <button className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`} onClick={() => setActiveTab('upload')}>
          <Upload size={18} />
          Document Ingestion
        </button>
      </div>

      {requestError && (
        <div className="alert-banner">
          <AlertTriangle size={18} />
          <span>{requestError}</span>
        </div>
      )}

      {activeTab === 'upload' && (
        <div className="view-grid">
          <div className="glass-panel">
            <h3 className="panel-title">
              <FileText size={20} />
              PDF Upload
            </h3>

            <div
              className={`upload-zone ${isDragOver ? 'dragging' : ''}`}
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="upload-icon-wrapper">
                <Upload size={28} />
              </div>
              <div>
                <p className="upload-text-main">Drag a specification PDF here</p>
                <p className="upload-text-sub">or click to browse files</p>
              </div>
              <input ref={fileInputRef} type="file" onChange={handleFileChange} accept="application/pdf" hidden />
            </div>

            {file && (
              <div className="selected-file-card">
                <div className="file-info">
                  <FileSpreadsheet size={18} className="brand-logo" />
                  <span className="file-name" title={file.name}>
                    {file.name}
                  </span>
                </div>
                <button className="remove-file-btn" onClick={() => setFile(null)} title="Remove file">
                  <Trash2 size={16} />
                </button>
              </div>
            )}

            <button
              className="btn btn-primary full-width-button"
              disabled={!file || uploading || serverStatus !== 'online'}
              onClick={triggerUpload}
            >
              {uploading ? (
                <>
                  <div className="spinner small-spinner" />
                  Extracting Rules
                </>
              ) : (
                <>
                  <Cpu size={18} />
                  Run Extraction
                </>
              )}
            </button>
          </div>

          <div className="glass-panel">
            {uploading ? (
              <div className="processing-overlay">
                <div className="spinner large-spinner" />
                <p className="processing-text">Running document extraction</p>
                <p className="processing-sub">Parsing, chunking, and assembling candidate rules.</p>
              </div>
            ) : extractedRules.length > 0 ? (
              <>
                <div className="results-header-section">
                  <div>
                    <h3 className="panel-title inline-title">
                      Extracted Candidate Rules
                      <span className="count-badge">{extractedRules.length} found</span>
                    </h3>
                    <p className="muted-copy">Selected rules can be sent directly to the rule compiler.</p>
                  </div>
                  <div className="results-actions">
                    <button className="btn btn-secondary btn-icon-only" title="Toggle select all" onClick={toggleSelectAll}>
                      <CheckCircle size={18} />
                    </button>
                    <button className="btn btn-primary" onClick={sendToBuilder}>
                      Send to Compiler
                      <ArrowRight size={16} />
                    </button>
                  </div>
                </div>

                <div className="rules-list">
                  {extractedRules.map((rule, index) => {
                    const isSelected = selectedRules.has(index);
                    return (
                      <button
                        key={`${rule.rule_text}-${index}`}
                        className={`rule-card selectable-card ${isSelected ? 'is-selected' : ''}`}
                        onClick={() => toggleRuleSelection(index)}
                      >
                        <div className="rule-card-header">
                          <span>Rule #{index + 1}</span>
                          {isSelected && <span className="selected-label">Selected</span>}
                        </div>
                        <div className="rule-text-block">
                          {rule.rule_text !== rule.resolved_rule_text && (
                            <>
                              <div className="rule-text-label">Verbatim</div>
                              <div className="rule-text-verbatim">{rule.rule_text}</div>
                            </>
                          )}
                          <div className="rule-text-label">Resolved Context</div>
                          <div className="rule-text-resolved">{rule.resolved_rule_text || rule.rule_text}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="empty-state">
                <FileText size={48} className="empty-state-icon" />
                <div>
                  <h4>No rules extracted yet</h4>
                  <p>Upload a PDF guideline document to mine candidate rules.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'formalize' && (
        <div className="view-grid">
          <div className="glass-panel">
            <h3 className="panel-title">
              <Cpu size={20} />
              Rule Input
            </h3>

            <label className="field-label">Formalizer Mode</label>
            <div className="segmented-control">
              <button
                className={`segment-btn ${formalizerMode === 'taxonomy' ? 'active' : ''}`}
                onClick={() => setFormalizerMode('taxonomy')}
              >
                Taxonomy V3
              </button>
              <button
                className={`segment-btn ${formalizerMode === 'legacy' ? 'active' : ''}`}
                onClick={() => setFormalizerMode('legacy')}
              >
                Legacy DFM
              </button>
            </div>

            <label className="field-label" htmlFor="domainOverride">
              Domain override
            </label>
            <select
              id="domainOverride"
              className="select-field"
              value={domainOverride}
              onChange={(event) => setDomainOverride(event.target.value)}
            >
              {DOMAIN_OPTIONS.map((domain) => (
                <option key={domain.label} value={domain.value}>
                  {domain.label}
                </option>
              ))}
            </select>

            <label className="field-label" htmlFor="ruleInput">
              Rules
            </label>
            <textarea
              id="ruleInput"
              className="input-field rule-textarea"
              placeholder="Enter one manufacturing rule per line."
              value={ruleInput}
              onChange={(event) => setRuleInput(event.target.value)}
            />

            <div className="button-row">
              <button className="btn btn-secondary" onClick={() => setRulesFromLines(SAMPLE_RULES)}>
                Load Samples
              </button>
              <button className="btn btn-secondary" onClick={() => setRulesFromLines([])} disabled={!ruleInput.trim()}>
                Clear
              </button>
            </div>

            <button
              className="btn btn-primary full-width-button"
              disabled={processing || !ruleInput.trim() || serverStatus !== 'online'}
              onClick={runFormalization}
            >
              {processing ? (
                <>
                  <div className="spinner small-spinner" />
                  Processing
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  Run Formalizer
                </>
              )}
            </button>

            <p className="api-note">
              Calls POST {formalizerMode === 'taxonomy' ? '/process-rules-taxonomy' : '/process-rules'}
            </p>
          </div>

          <div className="glass-panel">
            {processing ? (
              <div className="processing-overlay">
                <div className="spinner large-spinner" />
                <p className="processing-text">Running formalization</p>
                <p className="processing-sub">
                  {formalizerMode === 'taxonomy'
                    ? 'Classifying, extracting flat JSON, assembling nested arrays, and validating.'
                    : 'Resolving categories, equations, and formatter output.'}
                </p>
              </div>
            ) : formalizedRules.length > 0 ? (
              <>
                <div className="results-header-section">
                  <div>
                    <h3 className="panel-title inline-title">
                      Formalizer Results
                      <span className="count-badge">{formalizedRules.length} returned</span>
                    </h3>
                    <p className="muted-copy">
                      {formalizerMode === 'taxonomy' ? 'Taxonomy formalizer V3 response.' : 'Legacy formalizer response.'}
                    </p>
                  </div>
                  <div className="results-actions">
                    <button className="btn btn-secondary" onClick={exportResults}>
                      <Download size={16} />
                      Export JSON
                    </button>
                    <button className="btn btn-secondary btn-icon-only" title="Copy all results" onClick={() => copyToClipboard(formalizedRules)}>
                      <Copy size={16} />
                    </button>
                  </div>
                </div>

                <div className="formalized-grid">
                  {formalizedRules.map((result, index) =>
                    formalizerMode === 'taxonomy'
                      ? renderTaxonomyOutput(result, index)
                      : renderLegacyOutput(result, index)
                  )}
                </div>
              </>
            ) : (
              <div className="empty-state">
                <FileJson size={48} className="empty-state-icon" />
                <div>
                  <h4>No compiled output yet</h4>
                  <p>Run the compiler to inspect formatted rule JSON.</p>
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
