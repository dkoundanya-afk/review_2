/**
 * frontend/src/screens/TeacherDashboardScreen.jsx
 * Phase 4: Teacher Class Dashboard and Class Analytics Screen.
 * Displays real data from GET /api/teacher/classes/<id>/overview:
 * - Class metadata and join code with copy button
 * - Key Performance Indicators (KPIs): Enrolled, Active (7d), Quizzes, Avg Score, Completion %, No-Lab-Data
 * - 14-Day Participation Trend visual activity bars (Redemptions, Quizzes, Active students)
 * - Per-Salt Salt Analysis Matrix with blue cation chips & orange anion chips (Hard Rule 7)
 * - Inactive / Needs Attention students list
 * - Data transparency notice
 */
import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api, { getTranslatedError } from "../api.js";
import { IonChip, FormattedFormula } from "../components/IonDisplay.jsx";

export default function TeacherDashboardScreen() {
  const { id } = useParams();
  const { t, i18n } = useTranslation();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [copiedCode, setCopiedCode] = useState(false);
  const [downloadingReport, setDownloadingReport] = useState(null);
  const [exportError, setExportError] = useState("");
  const [exportSuccess, setExportSuccess] = useState("");

  const handleExport = async (type, filename) => {
    setDownloadingReport(type);
    setExportError("");
    setExportSuccess("");
    try {
      await api.download(`/teacher/classes/${id}/export/${type}`, filename);
      setExportSuccess(t("teacher_exports.download_success", { file: filename }));
      setTimeout(() => setExportSuccess(""), 4000);
    } catch (err) {
      setExportError(getTranslatedError(t, err) || t("teacher_exports.download_error"));
    } finally {
      setDownloadingReport(null);
    }
  };

  // Fetch overview data from backend
  const fetchOverview = useCallback(async (isSilent = false) => {
    if (!isSilent) setRefreshing(true);
    setErrorMsg("");
    try {
      const res = await api.get(`/teacher/classes/${id}/overview`);
      setData(res);
    } catch (err) {
      setErrorMsg(getTranslatedError(t, err) || t("teacher_dashboard.error_loading"));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id, t]);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      try {
        const res = await api.get(`/teacher/classes/${id}/overview`);
        if (isMounted) {
          setData(res);
          document.title = `${res?.class?.name || "Class"} — ${t("teacher_dashboard.title")}`;
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setErrorMsg(getTranslatedError(t, err) || t("teacher_dashboard.error_loading"));
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [id, t, i18n.language]);

  const handleCopyCode = async (code) => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(code);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = code;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    } catch {
      // Fallback ignore
    }
  };

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary mb-3" role="status" style={{ width: "3rem", height: "3rem" }}>
          <span className="visually-hidden">{t("common.loading")}</span>
        </div>
        <p className="text-muted fw-semibold">{t("common.loading")}</p>
      </div>
    );
  }

  if (errorMsg || !data) {
    return (
      <div className="py-4">
        <div className="mb-3">
          <Link to="/teacher/classes" className="btn btn-outline-secondary btn-sm">
            {t("teacher_dashboard.back_to_classes")}
          </Link>
        </div>
        <div className="alert alert-danger shadow-sm" role="alert">
          <h4 className="alert-heading fw-bold">⚠️ {t("teacher_dashboard.error_loading")}</h4>
          <p className="mb-0">{errorMsg || "Class not found or access denied."}</p>
        </div>
      </div>
    );
  }

  const { class: cls, kpis, salts, trend, inactive_students, visibility_notice } = data;

  // Max value for trend chart scaling
  const maxTrendVal = Math.max(
    1,
    ...trend.map((d) => Math.max(d.redemptions, d.quizzes, d.active_students))
  );

  return (
    <div className="teacher-dashboard pb-5">
      {/* Top Bar Navigation & Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <Link to="/teacher/classes" className="text-decoration-none text-muted small fw-semibold d-inline-flex align-items-center mb-1">
            {t("teacher_dashboard.back_to_classes")}
          </Link>
          <div className="d-flex align-items-center gap-2 flex-wrap">
            <h1 className="h3 fw-bold mb-0 text-dark">{cls.name}</h1>
            {cls.grade && (
              <span className="badge bg-secondary-subtle text-secondary border px-2 py-1">
                Grade {cls.grade} {cls.section ? `· Sec ${cls.section}` : ""}
              </span>
            )}
            {cls.active ? (
              <span className="badge bg-success-subtle text-success border border-success-subtle px-2 py-1">
                ● {t("teacher_dashboard.status_active")}
              </span>
            ) : (
              <span className="badge bg-secondary-subtle text-muted border px-2 py-1">
                📦 {t("teacher_dashboard.status_archived")}
              </span>
            )}
            {!cls.join_enabled && (
              <span className="badge bg-warning-subtle text-warning-emphasis border border-warning px-2 py-1">
                ⏸ {t("teacher_dashboard.join_paused")}
              </span>
            )}
          </div>
        </div>

        <div className="d-flex align-items-center gap-2">
          {/* Join Code Chip with Quick Copy */}
          <div className="d-flex align-items-center bg-white border rounded px-3 py-1 shadow-sm gap-2">
            <span className="text-muted small fw-medium">{t("teacher_dashboard.join_code")}</span>
            <span className="font-monospace fw-bold fs-6 text-primary">{cls.join_code}</span>
            <button
              type="button"
              className={`btn btn-sm py-0 px-2 fw-semibold ${copiedCode ? "btn-success" : "btn-outline-primary"}`}
              onClick={() => handleCopyCode(cls.join_code)}
              title={t("teacher_dashboard.copy_code")}
            >
              {copiedCode ? `✓ ${t("teacher_dashboard.code_copied")}` : t("teacher_dashboard.copy_code")}
            </button>
          </div>

          <Link
            to={`/teacher/classes/${cls.id}/insights`}
            className="btn btn-primary btn-sm fw-semibold shadow-sm d-inline-flex align-items-center gap-1"
          >
            <span>💡</span>
            <span>{t("teacher_dashboard.learning_insights_btn")}</span>
          </Link>

          <button
            type="button"
            className="btn btn-outline-secondary btn-sm fw-semibold shadow-sm"
            onClick={() => fetchOverview(false)}
            disabled={refreshing}
          >
            {refreshing ? (
              <>
                <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                {t("common.loading")}
              </>
            ) : (
              `🔄 ${t("teacher_dashboard.refresh")}`
            )}
          </button>
        </div>
      </div>

      {/* KPI METRIC CARDS */}
      <div className="row g-3 mb-4">
        {/* Total Students */}
        <div className="col-6 col-lg-2">
          <div className="card border-0 shadow-sm h-100 rounded-3 bg-white">
            <div className="card-body p-3 text-center">
              <span className="text-muted small fw-semibold text-uppercase d-block mb-1">
                👥 {t("teacher_dashboard.kpi_enrolled_title")}
              </span>
              <div className="display-6 fw-bold text-dark">{kpis.total_students}</div>
              <span className="text-muted small">{t("teacher_dashboard.kpi_enrolled_desc")}</span>
            </div>
          </div>
        </div>

        {/* Active Students (7 Days) */}
        <div className="col-6 col-lg-2">
          <div className="card border-0 shadow-sm h-100 rounded-3 bg-white">
            <div className="card-body p-3 text-center">
              <span className="text-muted small fw-semibold text-uppercase d-block mb-1">
                ⚡ {t("teacher_dashboard.kpi_active_title")}
              </span>
              <div className="display-6 fw-bold text-primary">{kpis.active_students_7d}</div>
              <span className="badge bg-primary-subtle text-primary border border-primary-subtle small">
                {t("teacher_dashboard.kpi_active_desc", { percent: kpis.participation_percent })}
              </span>
            </div>
          </div>
        </div>

        {/* Completed Quizzes */}
        <div className="col-6 col-lg-2">
          <div className="card border-0 shadow-sm h-100 rounded-3 bg-white">
            <div className="card-body p-3 text-center">
              <span className="text-muted small fw-semibold text-uppercase d-block mb-1">
                📝 {t("teacher_dashboard.kpi_quizzes_title")}
              </span>
              <div className="display-6 fw-bold text-success">{kpis.completed_graded_quizzes}</div>
              <span className="text-muted small">
                {t("teacher_dashboard.kpi_quizzes_desc", { redemptions: kpis.total_valid_redemptions })}
              </span>
            </div>
          </div>
        </div>

        {/* Average Quiz Score */}
        <div className="col-6 col-lg-2">
          <div className="card border-0 shadow-sm h-100 rounded-3 bg-white">
            <div className="card-body p-3 text-center">
              <span className="text-muted small fw-semibold text-uppercase d-block mb-1">
                🎯 {t("teacher_dashboard.kpi_avg_score_title")}
              </span>
              <div className="display-6 fw-bold text-info-emphasis">
                {kpis.avg_quiz_score_percent !== null ? `${kpis.avg_quiz_score_percent}%` : "—"}
              </div>
              <span className="text-muted small">{t("teacher_dashboard.kpi_avg_score_desc")}</span>
            </div>
          </div>
        </div>

        {/* Overall Completion */}
        <div className="col-6 col-lg-2">
          <div className="card border-0 shadow-sm h-100 rounded-3 bg-white">
            <div className="card-body p-3 text-center">
              <span className="text-muted small fw-semibold text-uppercase d-block mb-1">
                🏆 {t("teacher_dashboard.kpi_completion_title")}
              </span>
              <div className="display-6 fw-bold text-warning-emphasis">{kpis.overall_completion_percent}%</div>
              <span className="text-muted small">{t("teacher_dashboard.kpi_completion_desc")}</span>
            </div>
          </div>
        </div>

        {/* No Lab Data Count */}
        <div className="col-6 col-lg-2">
          <div className="card border-0 shadow-sm h-100 rounded-3 bg-white">
            <div className="card-body p-3 text-center">
              <span className="text-muted small fw-semibold text-uppercase d-block mb-1">
                ⚠️ {t("teacher_dashboard.kpi_no_data_title")}
              </span>
              <div className={`display-6 fw-bold ${kpis.no_lab_data_count > 0 ? "text-danger" : "text-secondary"}`}>
                {kpis.no_lab_data_count}
              </div>
              <span className="text-muted small">{t("teacher_dashboard.kpi_no_data_desc")}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Empty State Warning if 0 students */}
      {kpis.total_students === 0 && (
        <div className="alert alert-info border-info-subtle shadow-sm mb-4 p-4 text-center">
          <h4 className="fw-bold mb-2">📢 {t("teacher_dashboard.empty_class_title")}</h4>
          <p className="mb-0 text-muted">
            {t("teacher_dashboard.empty_class_desc", { code: cls.join_code })}
          </p>
        </div>
      )}

      {/* 14-DAY PARTICIPATION TREND CHART */}
      <div className="card border-0 shadow-sm rounded-3 mb-4 bg-white">
        <div className="card-header bg-white border-0 pt-4 px-4 pb-0 d-flex flex-wrap justify-content-between align-items-center gap-2">
          <div>
            <h2 className="h5 fw-bold mb-1 text-dark">📈 {t("teacher_dashboard.trend_title")}</h2>
            <p className="text-muted small mb-0">{t("teacher_dashboard.trend_subtitle")}</p>
          </div>
          {/* Legend */}
          <div className="d-flex align-items-center gap-3 small">
            <span className="d-flex align-items-center gap-1">
              <span className="d-inline-block rounded-circle" style={{ width: "10px", height: "10px", backgroundColor: "#0d6efd" }} />
              {t("teacher_dashboard.trend_redemptions")}
            </span>
            <span className="d-flex align-items-center gap-1">
              <span className="d-inline-block rounded-circle" style={{ width: "10px", height: "10px", backgroundColor: "#198754" }} />
              {t("teacher_dashboard.trend_quizzes")}
            </span>
            <span className="d-flex align-items-center gap-1">
              <span className="d-inline-block rounded-circle" style={{ width: "10px", height: "10px", backgroundColor: "#ffc107" }} />
              {t("teacher_dashboard.trend_active")}
            </span>
          </div>
        </div>

        <div className="card-body p-4">
          <div className="trend-chart-container" style={{ overflowX: "auto" }}>
            <div className="d-flex align-items-end justify-content-between gap-2 pt-4 pb-2" style={{ minWidth: "640px", height: "220px" }}>
              {trend.map((day) => {
                const dayLabel = day.date.slice(5); // e.g. "10-22"
                const redempHeight = Math.round((day.redemptions / maxTrendVal) * 140);
                const quizHeight = Math.round((day.quizzes / maxTrendVal) * 140);
                const activeHeight = Math.round((day.active_students / maxTrendVal) * 140);

                return (
                  <div key={day.date} className="d-flex flex-column align-items-center flex-grow-1" style={{ maxWidth: "48px" }}>
                    <div
                      className="d-flex align-items-end gap-1 mb-2 position-relative w-100 justify-content-center"
                      style={{ height: "150px" }}
                      title={`${day.date}: ${day.redemptions} redemptions, ${day.quizzes} quizzes, ${day.active_students} active`}
                    >
                      {/* Redemptions Bar */}
                      <div
                        className="rounded-top transition-all"
                        style={{
                          width: "8px",
                          height: `${Math.max(redempHeight, day.redemptions > 0 ? 4 : 0)}px`,
                          backgroundColor: "#0d6efd",
                        }}
                      />
                      {/* Quizzes Bar */}
                      <div
                        className="rounded-top transition-all"
                        style={{
                          width: "8px",
                          height: `${Math.max(quizHeight, day.quizzes > 0 ? 4 : 0)}px`,
                          backgroundColor: "#198754",
                        }}
                      />
                      {/* Active Students Bar */}
                      <div
                        className="rounded-top transition-all"
                        style={{
                          width: "8px",
                          height: `${Math.max(activeHeight, day.active_students > 0 ? 4 : 0)}px`,
                          backgroundColor: "#ffc107",
                        }}
                      />
                    </div>
                    <span className="text-muted small font-monospace" style={{ fontSize: "0.72rem" }}>
                      {dayLabel}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* PER-SALT SALT ANALYSIS MATRIX */}
      <div className="card border-0 shadow-sm rounded-3 mb-4 bg-white">
        <div className="card-header bg-white border-0 pt-4 px-4 pb-2">
          <h2 className="h5 fw-bold mb-1 text-dark">🧪 {t("teacher_dashboard.salts_title")}</h2>
          <p className="text-muted small mb-0">{t("teacher_dashboard.salts_subtitle")}</p>
        </div>

        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0 text-nowrap">
              <thead className="table-light text-muted small text-uppercase">
                <tr>
                  <th className="ps-4 py-3">{t("teacher_dashboard.salt_col_salt")}</th>
                  <th className="py-3">{t("teacher_dashboard.salt_col_ions")}</th>
                  <th className="py-3 text-center">{t("teacher_dashboard.salt_col_completed")}</th>
                  <th className="py-3 text-center">{t("teacher_dashboard.salt_col_avg_score")}</th>
                  <th className="py-3 text-center">{t("teacher_dashboard.salt_col_avg_duration")}</th>
                  <th className="py-3 pe-4 text-center">{t("teacher_dashboard.salt_col_no_lab")}</th>
                </tr>
              </thead>
              <tbody>
                {salts.map((s) => {
                  return (
                    <tr key={s.key}>
                      {/* Salt Formula & Name */}
                      <td className="ps-4 py-3">
                        <div className="d-flex align-items-center gap-2">
                          <span className="fs-6 fw-bold text-dark font-monospace">
                            <FormattedFormula formula={s.formula} />
                          </span>
                          <span className="text-muted small">({s.name})</span>
                        </div>
                      </td>

                      {/* Ion Chips: Blue Cation & Orange Anion (Hard Rule 7) */}
                      <td className="py-3">
                        <div className="d-flex align-items-center gap-1 flex-wrap">
                          <IonChip ionKey={s.cation} type="cation" showName={false} />
                          <IonChip ionKey={s.anion} type="anion" showName={false} />
                        </div>
                      </td>

                      {/* Completed Count & Progress Bar */}
                      <td className="py-3 text-center">
                        <div className="d-inline-flex flex-column align-items-center" style={{ width: "120px" }}>
                          <span className="small fw-semibold mb-1">
                            {s.completed_count} / {kpis.total_students} ({s.completion_percent}%)
                          </span>
                          <div className="progress w-100" style={{ height: "6px" }}>
                            <div
                              className="progress-bar bg-success"
                              role="progressbar"
                              style={{ width: `${s.completion_percent}%` }}
                              aria-valuenow={s.completion_percent}
                              aria-valuemin="0"
                              aria-valuemax="100"
                            />
                          </div>
                        </div>
                      </td>

                      {/* Average Score */}
                      <td className="py-3 text-center">
                        {s.avg_score_percent !== null ? (
                          <span
                            className={`badge px-2 py-1 fs-6 fw-semibold ${
                              s.avg_score_percent >= 75
                                ? "bg-success-subtle text-success border border-success-subtle"
                                : s.avg_score_percent >= 50
                                ? "bg-warning-subtle text-warning-emphasis border border-warning"
                                : "bg-danger-subtle text-danger border border-danger-subtle"
                            }`}
                          >
                            {s.avg_score_percent}%
                          </span>
                        ) : (
                          <span className="text-muted small fst-italic">
                            {t("teacher_dashboard.no_attempts_yet")}
                          </span>
                        )}
                      </td>

                      {/* Average Duration */}
                      <td className="py-3 text-center text-muted small">
                        {s.avg_duration_seconds !== null ? (
                          <span className="font-monospace fw-semibold text-dark">
                            {Math.floor(s.avg_duration_seconds / 60)}m {Math.round(s.avg_duration_seconds % 60)}s
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>

                      {/* No Lab Data Count */}
                      <td className="py-3 pe-4 text-center">
                        {s.no_lab_data_count > 0 ? (
                          <span className="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1">
                            ⚠️ {s.no_lab_data_count}
                          </span>
                        ) : (
                          <span className="text-success small">✓ 0</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* STUDENTS NEEDING ATTENTION (INACTIVE) */}
      <div className="card border-0 shadow-sm rounded-3 mb-4 bg-white">
        <div className="card-header bg-white border-0 pt-4 px-4 pb-2">
          <h2 className="h5 fw-bold mb-1 text-dark">⚠️ {t("teacher_dashboard.inactive_title")}</h2>
          <p className="text-muted small mb-0">{t("teacher_dashboard.inactive_subtitle")}</p>
        </div>

        <div className="card-body p-4">
          {inactive_students.length === 0 ? (
            <div className="alert alert-success border-success-subtle mb-0 py-3 px-4 d-flex align-items-center gap-2">
              <span className="fs-5">🎉</span>
              <span className="fw-semibold">{t("teacher_dashboard.inactive_empty")}</span>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-sm table-hover align-middle mb-0">
                <thead className="table-light text-muted small text-uppercase">
                  <tr>
                    <th className="py-2">{t("teacher_dashboard.col_student_id")}</th>
                    <th className="py-2">{t("teacher_dashboard.col_student_name")}</th>
                    <th className="py-2">{t("teacher_dashboard.col_joined_at")}</th>
                  </tr>
                </thead>
                <tbody>
                  {inactive_students.map((st) => (
                    <tr key={st.student_id}>
                      <td className="py-2 font-monospace fw-bold text-primary">{st.student_id}</td>
                      <td className="py-2 fw-semibold text-dark">{st.display_name}</td>
                      <td className="py-2 text-muted small">{new Date(st.joined_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* EXPORT REPORTS SECTION (Phase 7) */}
      <div className="card border-0 shadow-sm rounded-3 mb-4 bg-white">
        <div className="card-header bg-white border-0 pt-4 px-4 pb-2">
          <h2 className="h5 fw-bold mb-1 text-dark">📥 {t("teacher_exports.section_title")}</h2>
          <p className="text-muted small mb-0">{t("teacher_exports.section_subtitle")}</p>
        </div>

        <div className="card-body p-4">
          {exportError && (
            <div className="alert alert-danger py-2 px-3 small mb-3" role="alert">
              ⚠️ {exportError}
            </div>
          )}
          {exportSuccess && (
            <div className="alert alert-success py-2 px-3 small mb-3" role="alert">
              ✓ {exportSuccess}
            </div>
          )}

          <div className="row g-3">
            {/* 1. Class Roster */}
            <div className="col-12 col-md-6 col-lg-4">
              <div className="p-3 border rounded-3 h-100 d-flex flex-column justify-content-between bg-light-subtle">
                <div>
                  <div className="d-flex align-items-center gap-2 mb-1">
                    <span className="fs-5">📋</span>
                    <h3 className="h6 fw-bold mb-0 text-dark">{t("teacher_exports.roster_title")}</h3>
                  </div>
                  <p className="text-muted small mb-3">{t("teacher_exports.roster_desc")}</p>
                </div>
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm fw-semibold w-100 shadow-sm"
                  onClick={() => handleExport("roster", `virtulab_class_${cls.join_code}_roster.csv`)}
                  disabled={downloadingReport !== null}
                >
                  {downloadingReport === "roster" ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                      {t("common.loading")}
                    </>
                  ) : (
                    `⬇️ ${t("teacher_exports.download_btn")}`
                  )}
                </button>
              </div>
            </div>

            {/* 2. Quiz Results */}
            <div className="col-12 col-md-6 col-lg-4">
              <div className="p-3 border rounded-3 h-100 d-flex flex-column justify-content-between bg-light-subtle">
                <div>
                  <div className="d-flex align-items-center gap-2 mb-1">
                    <span className="fs-5">📝</span>
                    <h3 className="h6 fw-bold mb-0 text-dark">{t("teacher_exports.quizzes_title")}</h3>
                  </div>
                  <p className="text-muted small mb-3">{t("teacher_exports.quizzes_desc")}</p>
                </div>
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm fw-semibold w-100 shadow-sm"
                  onClick={() => handleExport("quiz-results", `virtulab_class_${cls.join_code}_quiz_results.csv`)}
                  disabled={downloadingReport !== null}
                >
                  {downloadingReport === "quiz-results" ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                      {t("common.loading")}
                    </>
                  ) : (
                    `⬇️ ${t("teacher_exports.download_btn")}`
                  )}
                </button>
              </div>
            </div>

            {/* 3. Practical Records */}
            <div className="col-12 col-md-6 col-lg-4">
              <div className="p-3 border rounded-3 h-100 d-flex flex-column justify-content-between bg-light-subtle">
                <div>
                  <div className="d-flex align-items-center gap-2 mb-1">
                    <span className="fs-5">🔬</span>
                    <h3 className="h6 fw-bold mb-0 text-dark">{t("teacher_exports.practicals_title")}</h3>
                  </div>
                  <p className="text-muted small mb-3">{t("teacher_exports.practicals_desc")}</p>
                </div>
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm fw-semibold w-100 shadow-sm"
                  onClick={() => handleExport("practical-records", `virtulab_class_${cls.join_code}_practical_records.csv`)}
                  disabled={downloadingReport !== null}
                >
                  {downloadingReport === "practical-records" ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                      {t("common.loading")}
                    </>
                  ) : (
                    `⬇️ ${t("teacher_exports.download_btn")}`
                  )}
                </button>
              </div>
            </div>

            {/* 4. Salt Performance */}
            <div className="col-12 col-md-6 col-lg-6">
              <div className="p-3 border rounded-3 h-100 d-flex flex-column justify-content-between bg-light-subtle">
                <div>
                  <div className="d-flex align-items-center gap-2 mb-1">
                    <span className="fs-5">🧪</span>
                    <h3 className="h6 fw-bold mb-0 text-dark">{t("teacher_exports.salts_title")}</h3>
                  </div>
                  <p className="text-muted small mb-3">{t("teacher_exports.salts_desc")}</p>
                </div>
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm fw-semibold w-100 shadow-sm"
                  onClick={() => handleExport("salt-performance", `virtulab_class_${cls.join_code}_salt_performance.csv`)}
                  disabled={downloadingReport !== null}
                >
                  {downloadingReport === "salt-performance" ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                      {t("common.loading")}
                    </>
                  ) : (
                    `⬇️ ${t("teacher_exports.download_btn")}`
                  )}
                </button>
              </div>
            </div>

            {/* 5. Learning Insights */}
            <div className="col-12 col-md-6 col-lg-6">
              <div className="p-3 border rounded-3 h-100 d-flex flex-column justify-content-between bg-light-subtle">
                <div>
                  <div className="d-flex align-items-center gap-2 mb-1">
                    <span className="fs-5">💡</span>
                    <h3 className="h6 fw-bold mb-0 text-dark">{t("teacher_exports.insights_title")}</h3>
                  </div>
                  <p className="text-muted small mb-3">{t("teacher_exports.insights_desc")}</p>
                </div>
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm fw-semibold w-100 shadow-sm"
                  onClick={() => handleExport("learning-insights", `virtulab_class_${cls.join_code}_learning_insights.csv`)}
                  disabled={downloadingReport !== null}
                >
                  {downloadingReport === "learning-insights" ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                      {t("common.loading")}
                    </>
                  ) : (
                    `⬇️ ${t("teacher_exports.download_btn")}`
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* VISIBILITY DISCLAIMER NOTICE (Spec B3) */}
      <div className="alert alert-secondary border-0 shadow-sm p-3 small text-muted d-flex align-items-start gap-2">
        <span className="fs-6">ℹ️</span>
        <div>
          <span className="fw-bold d-block text-dark">{t("teacher_dashboard.visibility_notice_title")}</span>
          <span>{visibility_notice}</span>
        </div>
      </div>
    </div>
  );
}
