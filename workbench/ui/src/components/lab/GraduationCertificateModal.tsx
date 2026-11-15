import React, { useState, useEffect } from "react";
import { CertificateResponse } from "../../types";
import { generateCertificate } from "../../api";
import { getCompletedLabs } from "../../utils/labProgress";

interface GraduationCertificateModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const GraduationCertificateModal: React.FC<GraduationCertificateModalProps> = ({
  isOpen,
  onClose
}) => {
  const [studentName, setStudentName] = useState<string>(() => {
    return localStorage.getItem("utss_student_name") || "Compiler Scholar";
  });
  const [certData, setCertData] = useState<CertificateResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCert = async (nameToUse: string) => {
    setLoading(true);
    setError(null);
    try {
      const completedMap = getCompletedLabs();
      const completedIds = Object.keys(completedMap);
      const res = await generateCertificate(nameToUse, completedIds);
      setCertData(res);
    } catch (err: any) {
      setError(err.message || "Failed to generate certificate");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchCert(studentName);
    }
  }, [isOpen]);

  const handleNameChange = (newName: string) => {
    setStudentName(newName);
    localStorage.setItem("utss_student_name", newName);
  };

  const handleUpdateCert = () => {
    fetchCert(studentName);
  };

  const handlePrint = () => {
    window.print();
  };

  if (!isOpen) return null;

  return (
    <div className="certificate-modal-overlay" onClick={onClose}>
      <div className="certificate-modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Controls Bar */}
        <div className="cert-controls-bar">
          <div className="name-input-group">
            <label className="cert-label">Scholar Name:</label>
            <input
              type="text"
              className="cert-name-input"
              value={studentName}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Enter your name..."
            />
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleUpdateCert}
              disabled={loading}
            >
              Update
            </button>
          </div>

          <div className="cert-actions-group">
            <button
              type="button"
              className="btn btn-primary btn-sm btn-print"
              onClick={handlePrint}
            >
              🖨️ Print / Save PDF
            </button>
            <button
              type="button"
              className="btn btn-icon btn-sm btn-close-cert"
              onClick={onClose}
              title="Close modal"
            >
              ✕
            </button>
          </div>
        </div>

        {error && (
          <div className="cert-error-banner">
            <span>⚠️ {error}</span>
          </div>
        )}

        {/* The Printable Certificate Document */}
        {loading ? (
          <div className="cert-loading">
            <div className="spinner" />
            <p>Cryptographically verifying lab completions & synthesizing certificate...</p>
          </div>
        ) : certData ? (
          <div className="printable-certificate-document">
            <div className="cert-ornament-border">
              <div className="cert-inner-content">
                {/* Certificate Header */}
                <div className="cert-document-header">
                  <div className="cert-seal">UTSS</div>
                  <h4 className="cert-institution">UNIVERSAL TYPE SYSTEM SCHEMAS</h4>
                  <span className="cert-subtitle">ACADEMIC COUNCIL ON COMPILER DESIGN & INTERMEDIATE REPRESENTATIONS</span>
                </div>

                <div className="cert-divider-line" />

                {/* Main Proclamation */}
                <div className="cert-proclamation">
                  <span className="cert-intro">This accredited document proudly certifies that</span>
                  <h1 className="cert-recipient-name">{certData.student_name}</h1>
                  <p className="cert-body-text">
                    has rigorously demonstrated empirical mastery across compiler AST syntax analysis,
                    multi-pass IR transformations, standard library type taxonomy, and cross-runtime
                    impedance verification.
                  </p>
                </div>

                {/* Tier Badge */}
                <div className="cert-tier-badge-container">
                  <span className="tier-tag">HONORARY RANK & TIER</span>
                  <h2 className="tier-title">{certData.mastery_tier}</h2>
                  <span className="tier-stats">
                    {certData.total_solved} of {certData.total_challenges} Challenges Solved ({certData.completion_ratio}% Completion) • {certData.total_xp_earned} / {certData.total_xp_available} XP
                  </span>
                </div>

                {/* Badges Earned */}
                <div className="cert-badges-grid">
                  {certData.badges.map((b, idx) => (
                    <div key={idx} className="cert-badge-item">
                      <span className="badge-icon">{b.icon}</span>
                      <span className="badge-text">{b.title}</span>
                    </div>
                  ))}
                </div>

                {/* Signatures & Verification Hash */}
                <div className="cert-footer-grid">
                  <div className="footer-col">
                    <span className="sig-line" />
                    <span className="sig-name">Antigravity AI</span>
                    <span className="sig-title">DeepMind Compiler Agent</span>
                  </div>

                  <div className="footer-col seal-col">
                    <div className="cert-official-seal">
                      <span>VERIFIED</span>
                      <span className="seal-year">2026</span>
                    </div>
                  </div>

                  <div className="footer-col">
                    <span className="sig-line" />
                    <span className="sig-name">Issue Date: {certData.issue_date}</span>
                    <span className="sig-token">Verification: <code>{certData.verification_token}</code></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
