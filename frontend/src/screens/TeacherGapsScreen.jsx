/**
 * frontend/src/screens/TeacherGapsScreen.jsx
 * Phase 6: Teacher Learning Gaps & Student Performance Insights Screen.
 * Displays evidence-based learning analytics from GET /api/teacher/classes/<id>/learning-insights:
 * - Summary KPI cards (Topics with gaps, salts with data, lab mistakes, students needing support)
 * - Topic-wise learning gap analysis with minimum evidence thresholds (n >= 10)
 * - 12-Salt performance matrix with blue cation chips & orange anion chips
 * - Practical mistake telemetry analysis with explicit denominators
 * - Evidence-based list of students who may benefit from support
 * - Full i18n support in English and Kannada
 */
import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api, { getTranslatedError } from "../api.js";
import { IonChip, FormattedFormula } from "../components/IonDisplay.jsx";

export default function TeacherGapsScreen() {
  const { id } = useParams();
  const { t, i18n } = useTranslation();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [showInsufficient, setShowInsufficient] = useState(false);

  const fetchInsights = useCallback(async (isSilent = false) => {
    if (!isSilent) setRefreshing(true);
    setErrorMsg("");
    try {
      const res = await api.get(`/teacher/classes/${id}/learning-insights`);
      setData(res);
    } catch (err) {
      setErrorMsg(getTranslatedError(t, err) || t("teacher_insights.error_loading"));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id, t]);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      try {
        const res = await api.get(`/teacher/classes/${id}/learning-insights`);
        if (isMounted) {
          setData(res);
          document.title = `${res?.class?.name || "Class"} — ${t("teacher_insights.title")}`;
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setErrorMsg(getTranslatedError(t, err) || t("teacher_insights.error_loading"));
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [id, t, i18n.language]);

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
          <Link to={`/teacher/classes/${id}`} className="btn btn-outline-secondary btn-sm">
            {t("teacher_insights.back_to_dashboard")}
          </Link>
        </div>
        <div className="alert alert-danger shadow-sm" role="alert">
          <h4 className="alert-heading fw-bold">⚠️ {t("teacher_insights.error_loading")}</h4>
          <p className="mb-0">{errorMsg || "Class not found or access denied."}</p>
        </div>
      </div>
    );
  }

  const { class: cls, summary, topics, salts, practical_mistakes, students_needing_support, notice } = data;

  const sufficientTopics = topics.filter((tItem) => tItem.sufficient_evidence);
  const insufficientTopics = topics.filter((tItem) => !tItem.sufficient_evidence);

  return (
    <div className="teacher-insights pb-5">
      {/* Top Header & Breadcrumb */}
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <div>
          <Link
            to={`/teacher/classes/${cls.id}`}
            className="text-decoration-none text-muted small fw-semibold d-inline-flex align-items-center mb-1"
          >
            {t("teacher_insights.back_to_dashboard")}
          </Link>
          <div className="d-flex align-items-center gap-2 flex-wrap">
            <h1 className="h3 fw-bold mb-0 text-dark">💡 {t("teacher_insights.title")}</h1>
            <span className="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1">
              {cls.name}
            </span>
            {cls.grade && (
              <span className="badge bg-secondary-subtle text-secondary border px-2 py-1">
                Grade {cls.grade} {cls.section ? `· Sec ${cls.section}` : ""}
              </span>
            )}
          </div>
          <p className="text-muted small mb-0 mt-1">{t("teacher_insights.subtitle")}</p>
        </div>

        <div className="d-flex align-items-center gap-2">
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm fw-semibold shadow-sm"
            onClick={() => fetchInsights(false)}
            disabled={refreshing}
          >
            {refreshing ? (
              <>
                <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                {t("common.loading")}
              </>
            ) : (
              `🔄 ${t("teacher_insights.refresh")}`
            )}
          </button>
        </div>
      </div>

      {/* OVERVIEW SUMMARY CARDS */}
      <div className="row g-3 mb-4">
        {/* Topics with Gaps */}
        <div className="col-6 col-lg-3">
          <div className="card border-0 shadow-sm h-100 rounded-3 bg-white">
            <div className="card-body p-3 text-center">
              <span className="text-muted small fw-semibold text-uppercase d-block mb-1">
                🎯 {t("teacher_insights.kpi_topics_gap_title")}
              </span>
              <div className={`display-6 fw-bold ${summary.topics_with_gaps_count > 0 ? "text-danger" : "text-success"}`}>
                {summary.topics_with_gaps_count}
              </div>
              <span className="text-muted small">{t("teacher_insights.kpi_topics_gap_desc")}</span>
            </div>
          </div>
        </div>

        {/* Salts with Data */}
        <div className="col-6 col-lg-3">
          <div className="card border-0 shadow-sm h-100 rounded-3 bg-white">
            <div className="card-body p-3 text-center">
              <span className="text-muted small fw-semibold text-uppercase d-block mb-1">
                🧪 {t("teacher_insights.kpi_salts_active_title")}
              </span>
              <div className="display-6 fw-bold text-primary">{summary.salts_with_data_count} / 12</div>
              <span className="text-muted small">{t("teacher_insights.kpi_salts_active_desc")}</span>
            </div>
          </div>
        </div>

        {/* Practical Mistakes Recorded */}
        <div className="col-6 col-lg-3">
          <div className="card border-0 shadow-sm h-100 rounded-3 bg-white">
            <div className="card-body p-3 text-center">
              <span className="text-muted small fw-semibold text-uppercase d-block mb-1">
                ⚠️ {t("teacher_insights.kpi_mistakes_title")}
              </span>
              <div className={`display-6 fw-bold ${summary.total_mistakes_recorded > 0 ? "text-warning-emphasis" : "text-secondary"}`}>
                {summary.has_telemetry ? summary.total_mistakes_recorded : "—"}
              </div>
              <span className="text-muted small">
                {summary.has_telemetry
                  ? t("teacher_insights.kpi_mistakes_desc", { tokens: summary.valid_tokens_count })
                  : t("teacher_insights.kpi_no_telemetry_desc")}
              </span>
            </div>
          </div>
        </div>

        {/* Students Needing Support */}
        <div className="col-6 col-lg-3">
          <div className="card border-0 shadow-sm h-100 rounded-3 bg-white">
            <div className="card-body p-3 text-center">
              <span className="text-muted small fw-semibold text-uppercase d-block mb-1">
                👥 {t("teacher_insights.kpi_support_title")}
              </span>
              <div className={`display-6 fw-bold ${summary.students_needing_support_count > 0 ? "text-danger" : "text-success"}`}>
                {summary.students_needing_support_count}
              </div>
              <span className="text-muted small">{t("teacher_insights.kpi_support_desc")}</span>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 1: TOPIC-WISE LEARNING GAP ANALYSIS */}
      <div className="card border-0 shadow-sm rounded-3 mb-4 bg-white">
        <div className="card-header bg-white border-0 pt-4 px-4 pb-2">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-2">
            <div>
              <h2 className="h5 fw-bold mb-1 text-dark">📊 {t("teacher_insights.topics_section_title")}</h2>
              <p className="text-muted small mb-0">{t("teacher_insights.topics_section_desc")}</p>
            </div>
            {insufficientTopics.length > 0 && (
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm py-1 px-2 small"
                onClick={() => setShowInsufficient(!showInsufficient)}
              >
                {showInsufficient ? "Hide Insufficient Data Topics" : `Show All Topics (${insufficientTopics.length} low-data)`}
              </button>
            )}
          </div>
        </div>

        <div className="card-body p-4">
          {topics.length === 0 ? (
            <div className="alert alert-info border-info-subtle mb-0 p-4 text-center">
              <p className="mb-0 text-muted">{t("teacher_insights.topics_empty")}</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light text-muted small text-uppercase">
                  <tr>
                    <th className="py-2">{t("teacher_insights.col_topic")}</th>
                    <th className="py-2 text-center">{t("teacher_insights.col_correct")}</th>
                    <th className="py-2 text-center">{t("teacher_insights.col_incorrect")}</th>
                    <th className="py-2 text-center">{t("teacher_insights.col_total")}</th>
                    <th className="py-2 text-center">{t("teacher_insights.col_accuracy")}</th>
                    <th className="py-2 text-center" style={{ minWidth: "140px" }}>
                      {t("teacher_insights.col_gap_score")}
                    </th>
                    <th className="py-2 text-center">{t("teacher_insights.col_evidence")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(showInsufficient ? topics : sufficientTopics).map((item) => {
                    const gapColor =
                      item.gap_score >= 0.5 ? "danger" : item.gap_score >= 0.3 ? "warning" : "success";
                    return (
                      <tr key={item.topic}>
                        <td className="py-3">
                          <span className="fw-bold text-dark d-block">{item.label}</span>
                          <span className="font-monospace text-muted small">tag: {item.topic}</span>
                        </td>
                        <td className="py-3 text-center text-success fw-semibold">{item.correct_answers}</td>
                        <td className="py-3 text-center text-danger fw-semibold">{item.incorrect_answers}</td>
                        <td className="py-3 text-center fw-bold">{item.total_answers}</td>
                        <td className="py-3 text-center">
                          <span className="badge bg-secondary-subtle text-dark border px-2 py-1">
                            {item.correct_percent}%
                          </span>
                        </td>
                        <td className="py-3 text-center">
                          <div className="d-flex align-items-center justify-content-center gap-2">
                            <div className="progress flex-grow-1" style={{ height: "8px", maxWidth: "80px" }}>
                              <div
                                className={`progress-bar bg-${gapColor}`}
                                role="progressbar"
                                style={{ width: `${Math.round(item.gap_score * 100)}%` }}
                                aria-valuenow={Math.round(item.gap_score * 100)}
                                aria-valuemin="0"
                                aria-valuemax="100"
                              />
                            </div>
                            <span className={`fw-bold small text-${gapColor}`}>{item.gap_score}</span>
                          </div>
                        </td>
                        <td className="py-3 text-center">
                          {item.sufficient_evidence ? (
                            <span className="badge bg-success-subtle text-success border border-success-subtle px-2 py-1">
                              ✓ {t("teacher_insights.evidence_sufficient")}
                            </span>
                          ) : (
                            <span className="badge bg-warning-subtle text-warning-emphasis border border-warning px-2 py-1">
                              ⚠️ {t("teacher_insights.evidence_insufficient")}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* SECTION 2: 12-SALT PERFORMANCE MATRIX */}
      <div className="card border-0 shadow-sm rounded-3 mb-4 bg-white">
        <div className="card-header bg-white border-0 pt-4 px-4 pb-2">
          <h2 className="h5 fw-bold mb-1 text-dark">🧪 {t("teacher_insights.salts_section_title")}</h2>
          <p className="text-muted small mb-0">{t("teacher_insights.salts_section_desc")}</p>
        </div>

        <div className="card-body p-4">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light text-muted small text-uppercase">
                <tr>
                  <th className="py-2 ps-3">{t("teacher_insights.col_salt")}</th>
                  <th className="py-2">{t("teacher_insights.col_ions")}</th>
                  <th className="py-2 text-center">{t("teacher_insights.col_students")}</th>
                  <th className="py-2 text-center">{t("teacher_insights.col_submissions")}</th>
                  <th className="py-2 text-center">{t("teacher_insights.col_avg_score")}</th>
                  <th className="py-2 text-center">{t("teacher_insights.col_accuracy_rate")}</th>
                  <th className="py-2 text-center">{t("teacher_insights.col_practical_done")}</th>
                  <th className="py-2 text-center pe-3">{t("teacher_insights.col_no_lab_data")}</th>
                </tr>
              </thead>
              <tbody>
                {salts.map((s) => (
                  <tr key={s.key}>
                    <td className="py-3 ps-3">
                      <div className="fw-bold text-dark">{s.name}</div>
                      <div className="small text-muted">
                        <FormattedFormula formula={s.formula} />
                      </div>
                    </td>
                    <td className="py-3">
                      <div className="d-flex align-items-center gap-1 flex-wrap">
                        <IonChip ionKey={s.cation} type="cation" showName={false} />
                        <IonChip ionKey={s.anion} type="anion" showName={false} />
                      </div>
                    </td>
                    <td className="py-3 text-center fw-semibold text-secondary">{s.students_with_quiz}</td>
                    <td className="py-3 text-center fw-bold">{s.valid_graded_submissions}</td>
                    <td className="py-3 text-center">
                      {s.avg_quiz_score_percent !== null ? (
                        <span className="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1">
                          {s.avg_quiz_score_percent}%
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="py-3 text-center">
                      {s.correct_answer_percent !== null ? (
                        <span className="badge bg-secondary-subtle text-dark border px-2 py-1">
                          {s.correct_answer_percent}%
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="py-3 text-center text-success fw-semibold">
                      {s.practical_completed_students}
                    </td>
                    <td className="py-3 text-center pe-3">
                      {s.no_lab_data_count > 0 ? (
                        <span className="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1">
                          ⚠️ {s.no_lab_data_count}
                        </span>
                      ) : (
                        <span className="text-success small">✓ 0</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* SECTION 3: PRACTICAL LAB MISTAKES ANALYSIS */}
      <div className="card border-0 shadow-sm rounded-3 mb-4 bg-white">
        <div className="card-header bg-white border-0 pt-4 px-4 pb-2">
          <h2 className="h5 fw-bold mb-1 text-dark">🔬 {t("teacher_insights.mistakes_section_title")}</h2>
          <p className="text-muted small mb-0">{t("teacher_insights.mistakes_section_desc")}</p>
        </div>

        <div className="card-body p-4">
          {!practical_mistakes.has_telemetry ? (
            <div className="alert alert-secondary border-0 shadow-sm p-4 text-center">
              <h5 className="fw-bold mb-2">ℹ️ {t("teacher_insights.no_telemetry_title")}</h5>
              <p className="mb-0 text-muted">{practical_mistakes.notice || t("teacher_insights.no_telemetry_desc")}</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light text-muted small text-uppercase">
                  <tr>
                    <th className="py-2">{t("teacher_insights.col_mistake_cat")}</th>
                    <th className="py-2 text-center">{t("teacher_insights.col_occurrences")}</th>
                    <th className="py-2 text-center">{t("teacher_insights.col_affected_students")}</th>
                    <th className="py-2 text-center">{t("teacher_insights.col_mistake_rate")}</th>
                    <th className="py-2">{t("teacher_insights.col_affected_salts")}</th>
                  </tr>
                </thead>
                <tbody>
                  {practical_mistakes.categories.map((m) => (
                    <tr key={m.category}>
                      <td className="py-3">
                        <span className="fw-bold text-dark d-block">{m.label}</span>
                        <span className="font-monospace text-muted small">{m.category}</span>
                      </td>
                      <td className="py-3 text-center">
                        <span className={`fw-bold ${m.occurrences > 0 ? "text-danger" : "text-muted"}`}>
                          {m.occurrences}
                        </span>
                      </td>
                      <td className="py-3 text-center fw-semibold text-secondary">{m.affected_students_count}</td>
                      <td className="py-3 text-center">
                        <span
                          className={`badge ${
                            m.rate_percent > 30
                              ? "bg-danger-subtle text-danger border-danger-subtle"
                              : m.rate_percent > 0
                              ? "bg-warning-subtle text-warning-emphasis border-warning"
                              : "bg-light text-muted border"
                          } border px-2 py-1`}
                        >
                          {m.rate_percent}%
                        </span>
                        <div className="text-muted" style={{ fontSize: "0.75rem" }}>
                          ({m.occurrences} / {practical_mistakes.denominator_tokens} tokens)
                        </div>
                      </td>
                      <td className="py-3">
                        {m.affected_salts.length > 0 ? (
                          <div className="d-flex align-items-center gap-1 flex-wrap">
                            {m.affected_salts.map((formula) => (
                              <span key={formula} className="badge bg-secondary-subtle text-dark border px-2 py-1">
                                <FormattedFormula formula={formula} />
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-muted small">None</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* SECTION 4: STUDENTS NEEDING SUPPORT */}
      <div className="card border-0 shadow-sm rounded-3 mb-4 bg-white">
        <div className="card-header bg-white border-0 pt-4 px-4 pb-2">
          <h2 className="h5 fw-bold mb-1 text-dark">🤝 {t("teacher_insights.support_section_title")}</h2>
          <p className="text-muted small mb-0">{t("teacher_insights.support_section_desc")}</p>
        </div>

        <div className="card-body p-4">
          {students_needing_support.length === 0 ? (
            <div className="alert alert-success border-success-subtle mb-0 py-3 px-4 d-flex align-items-center gap-2">
              <span className="fs-5">🎉</span>
              <span className="fw-semibold">{t("teacher_insights.support_empty")}</span>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light text-muted small text-uppercase">
                  <tr>
                    <th className="py-2">{t("teacher_insights.col_student")}</th>
                    <th className="py-2">{t("teacher_insights.col_evidence_reasons")}</th>
                    <th className="py-2 text-end">{t("teacher_insights.col_action")}</th>
                  </tr>
                </thead>
                <tbody>
                  {students_needing_support.map((st) => (
                    <tr key={st.student_id}>
                      <td className="py-3">
                        <div className="font-monospace fw-bold text-primary">{st.student_id}</div>
                        <div className="small fw-semibold text-dark">{st.display_name}</div>
                        <div className="text-muted" style={{ fontSize: "0.75rem" }}>
                          Enrolled: {new Date(st.joined_at).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="py-3">
                        <ul className="list-unstyled mb-0 d-flex flex-column gap-1">
                          {st.reasons.map((r, i) => (
                            <li key={i} className="small d-flex align-items-start gap-1">
                              <span className="text-danger">●</span>
                              <span>{r}</span>
                            </li>
                          ))}
                        </ul>
                      </td>
                      <td className="py-3 text-end">
                        <Link
                          to={`/teacher/classes/${cls.id}`}
                          className="btn btn-outline-primary btn-sm fw-semibold shadow-sm"
                        >
                          {t("teacher_insights.view_dashboard")}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* DATA PROVENANCE & NOTICE */}
      <div className="alert alert-secondary border-0 shadow-sm p-3 small text-muted d-flex align-items-start gap-2">
        <span className="fs-6">ℹ️</span>
        <div>
          <span className="fw-bold d-block text-dark">{t("teacher_insights.data_notice_title")}</span>
          <span>{notice || t("teacher_insights.data_notice_text")}</span>
        </div>
      </div>
    </div>
  );
}
