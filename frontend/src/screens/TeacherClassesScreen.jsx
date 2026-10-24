/**
 * frontend/src/screens/TeacherClassesScreen.jsx
 * Phase 3: Teacher Class Management Screen.
 * Full CRUD interface for authenticated teachers:
 * - List classes (active, archived, or all)
 * - Create new class (POST /api/teacher/classes)
 * - Edit class details & toggle join code (PATCH /api/teacher/classes/<id>)
 * - Rotate join code (PATCH /api/teacher/classes/<id> with rotate_join_code: true)
 * - Archive / Restore class (PATCH /api/teacher/classes/<id> with active: false/true)
 * - Copy join code with visual feedback
 * - Strict backend teacher isolation enforced
 */
import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api, { getTranslatedError } from "../api.js";

export default function TeacherClassesScreen() {
  const { t, i18n } = useTranslation();

  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [filter, setFilter] = useState("active"); // 'active' | 'archived' | 'all'
  const [copiedCode, setCopiedCode] = useState(null);

  // Create Class Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({ name: "", grade: "", section: "" });
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState("");

  // Edit Class Modal State
  const [editingClass, setEditingClass] = useState(null);
  const [editForm, setEditForm] = useState({
    name: "",
    grade: "",
    section: "",
    join_enabled: true,
    rotate_join_code: false,
  });
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState("");

  // Archive / Restore Confirmation Modal State
  const [confirmAction, setConfirmAction] = useState(null); // { type: 'archive' | 'restore', cls: object }
  const [confirmSubmitting, setConfirmSubmitting] = useState(false);

  // Fetch classes from backend API
  const fetchClasses = useCallback(async (isSilent = false) => {
    if (!isSilent) setRefreshing(true);
    setErrorMsg("");
    try {
      const data = await api.get("/teacher/classes");
      setClasses(Array.isArray(data) ? data : []);
    } catch (err) {
      setErrorMsg(getTranslatedError(t, err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [t]);

  useEffect(() => {
    document.title = `${t("teacher_classes.title")} — ${t("app_name")}`;
    let isMounted = true;

    async function load() {
      try {
        const data = await api.get("/teacher/classes");
        if (isMounted) {
          setClasses(Array.isArray(data) ? data : []);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setErrorMsg(getTranslatedError(t, err));
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      isMounted = false;
    };
  }, [t, i18n.language]);

  // Handle Copy Join Code
  const handleCopyCode = async (code) => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(code);
      } else {
        // Fallback for older browsers
        const textarea = document.createElement("textarea");
        textarea.value = code;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch {
      // Ignore clipboard write failures
    }
  };

  // Open Create Class Modal
  const openCreateModal = () => {
    setCreateForm({ name: "", grade: "", section: "" });
    setCreateError("");
    setShowCreateModal(true);
  };

  // Submit Create Class
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setCreateError("");

    const name = createForm.name.trim();
    if (!name) {
      setCreateError(t("errors.name_required"));
      return;
    }

    setCreateSubmitting(true);
    try {
      const payload = {
        name,
        grade: createForm.grade.trim(),
        section: createForm.section.trim(),
      };
      const created = await api.post("/teacher/classes", payload);
      setShowCreateModal(false);
      setSuccessMsg(t("teacher_classes.success_created", { name: created.name, code: created.join_code }));
      setTimeout(() => setSuccessMsg(""), 6000);
      await fetchClasses(true);
    } catch (err) {
      setCreateError(getTranslatedError(t, err));
    } finally {
      setCreateSubmitting(false);
    }
  };

  // Open Edit Class Modal
  const openEditModal = (cls) => {
    setEditingClass(cls);
    setEditForm({
      name: cls.name || "",
      grade: cls.grade || "",
      section: cls.section || "",
      join_enabled: cls.join_enabled ?? true,
      rotate_join_code: false,
    });
    setEditError("");
  };

  // Submit Edit Class
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setEditError("");

    const name = editForm.name.trim();
    if (!name) {
      setEditError(t("errors.name_required"));
      return;
    }

    setEditSubmitting(true);
    try {
      const payload = {
        name,
        grade: editForm.grade.trim(),
        section: editForm.section.trim(),
        join_enabled: editForm.join_enabled,
      };
      if (editForm.rotate_join_code) {
        payload.rotate_join_code = true;
      }
      const updated = await api.patch(`/teacher/classes/${editingClass.id}`, payload);
      setEditingClass(null);
      setSuccessMsg(t("teacher_classes.success_updated", { name: updated.name }));
      setTimeout(() => setSuccessMsg(""), 6000);
      await fetchClasses(true);
    } catch (err) {
      setEditError(getTranslatedError(t, err));
    } finally {
      setEditSubmitting(false);
    }
  };

  // Submit Archive or Restore Action
  const handleConfirmAction = async () => {
    if (!confirmAction) return;
    const { type, cls } = confirmAction;

    setConfirmSubmitting(true);
    try {
      const newActive = type === "restore";
      await api.patch(`/teacher/classes/${cls.id}`, { active: newActive });
      setConfirmAction(null);
      setSuccessMsg(
        newActive
          ? t("teacher_classes.success_restored", { name: cls.name })
          : t("teacher_classes.success_archived", { name: cls.name })
      );
      setTimeout(() => setSuccessMsg(""), 6000);
      await fetchClasses(true);
    } catch (err) {
      setErrorMsg(getTranslatedError(t, err));
      setConfirmAction(null);
    } finally {
      setConfirmSubmitting(false);
    }
  };

  // Counts for filter tabs
  const activeCount = classes.filter((c) => c.active).length;
  const archivedCount = classes.filter((c) => !c.active).length;

  // Filtered classes according to selected tab
  const displayedClasses = classes.filter((c) => {
    if (filter === "active") return c.active;
    if (filter === "archived") return !c.active;
    return true;
  });

  return (
    <div className="teacher-classes-screen pb-5">
      {/* Page Header */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <h1 className="h3 fw-bold mb-1">{t("teacher_classes.title")}</h1>
          <p className="text-muted small mb-0">{t("teacher_classes.subtitle")}</p>
        </div>

        <div className="d-flex align-items-center gap-2">
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm fw-semibold"
            onClick={() => fetchClasses(false)}
            disabled={refreshing || loading}
            aria-label={t("teacher_classes.refresh")}
          >
            {refreshing ? (
              <>
                <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                {t("common.loading")}
              </>
            ) : (
              `🔄 ${t("teacher_classes.refresh")}`
            )}
          </button>

          <button
            type="button"
            className="btn btn-primary btn-sm fw-bold px-3 shadow-sm"
            onClick={openCreateModal}
            id="btn-create-class"
          >
            + {t("teacher_classes.create_btn")}
          </button>
        </div>
      </div>

      {/* Global Notifications */}
      {successMsg && (
        <div className="alert alert-success alert-dismissible fade show py-2 px-3 small mb-4" role="status">
          ✓ {successMsg}
          <button
            type="button"
            className="btn-close py-2 px-3 small"
            onClick={() => setSuccessMsg("")}
            aria-label={t("teacher_classes.close")}
          />
        </div>
      )}

      {errorMsg && (
        <div className="alert alert-danger py-2 px-3 small mb-4" role="alert">
          {errorMsg}
        </div>
      )}

      {/* Filter Tabs */}
      {classes.length > 0 && (
        <div className="btn-group mb-4" role="tablist" aria-label="Class Filter">
          <button
            type="button"
            className={`btn btn-sm fw-semibold ${filter === "active" ? "btn-primary" : "btn-outline-primary"}`}
            onClick={() => setFilter("active")}
            aria-selected={filter === "active"}
          >
            {t("teacher_classes.filter_active", { count: activeCount })}
          </button>
          <button
            type="button"
            className={`btn btn-sm fw-semibold ${filter === "archived" ? "btn-primary" : "btn-outline-primary"}`}
            onClick={() => setFilter("archived")}
            aria-selected={filter === "archived"}
          >
            {t("teacher_classes.filter_archived", { count: archivedCount })}
          </button>
          <button
            type="button"
            className={`btn btn-sm fw-semibold ${filter === "all" ? "btn-primary" : "btn-outline-primary"}`}
            onClick={() => setFilter("all")}
            aria-selected={filter === "all"}
          >
            {t("teacher_classes.filter_all", { count: classes.length })}
          </button>
        </div>
      )}

      {/* Loading Skeleton / Empty State / Cards Grid */}
      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">{t("teacher_classes.loading")}</span>
          </div>
          <p className="text-muted small mt-2">{t("teacher_classes.loading")}</p>
        </div>
      ) : classes.length === 0 ? (
        <div className="card border-0 shadow-sm text-center py-5 px-3">
          <div className="card-body">
            <div className="fs-1 mb-2">🏫</div>
            <h2 className="h5 fw-bold mb-1">{t("teacher_classes.empty_title")}</h2>
            <p className="text-muted small mb-4">{t("teacher_classes.empty_hint")}</p>
            <button
              type="button"
              className="btn btn-primary fw-bold px-4"
              onClick={openCreateModal}
            >
              + {t("teacher_classes.create_first_class")}
            </button>
          </div>
        </div>
      ) : displayedClasses.length === 0 ? (
        <div className="card border-0 shadow-sm text-center py-4 px-3 text-muted">
          <p className="small mb-0">
            {filter === "archived" ? t("teacher_classes.no_archived_hint") : t("teacher_classes.empty_hint")}
          </p>
        </div>
      ) : (
        <div className="row g-3">
          {displayedClasses.map((cls) => {
            const studentCount = cls.students ?? 0;
            const studentText =
              studentCount === 1
                ? t("teacher_classes.students_count_one", { count: studentCount })
                : t("teacher_classes.students_count_other", { count: studentCount });

            const isCopied = copiedCode === cls.join_code;

            return (
              <div key={cls.id} className="col-12 col-md-6 col-lg-4">
                <div className={`card h-100 border-0 shadow-sm ${cls.active ? "" : "opacity-75 bg-light"}`}>
                  <div className="card-body d-flex flex-column p-4">
                    {/* Header: Class Name and Status Badges */}
                    <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
                      <h2 className="h5 fw-bold mb-0 text-truncate" title={cls.name}>
                        <Link to={`/teacher/classes/${cls.id}`} className="text-decoration-none text-dark">
                          {cls.name}
                        </Link>
                      </h2>
                      <div className="d-flex flex-wrap gap-1 justify-content-end">
                        <span
                          className={`badge ${
                            cls.active ? "bg-success-subtle text-success" : "bg-secondary-subtle text-secondary"
                          }`}
                        >
                          {cls.active ? t("teacher_classes.active_badge") : t("teacher_classes.inactive_badge")}
                        </span>
                        {!cls.join_enabled && cls.active && (
                          <span className="badge bg-warning-subtle text-warning-emphasis" title={t("teacher_classes.join_disabled_badge")}>
                            {t("teacher_classes.join_disabled_badge")}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Grade & Section Sub-label */}
                    <p className="text-muted small mb-3">
                      {[cls.grade && `Grade ${cls.grade}`, cls.section && `Sec ${cls.section}`]
                        .filter(Boolean)
                        .join(" • ") || "—"}
                    </p>

                    {/* Join Code Box */}
                    <div className="bg-light p-3 rounded border mb-3">
                      <div className="d-flex justify-content-between align-items-center">
                        <div>
                          <span className="text-muted small d-block mb-1">
                            {t("teacher_classes.join_code_label")}
                          </span>
                          <span className="font-monospace fw-bold text-primary fs-5 letter-spacing-2">
                            {cls.join_code}
                          </span>
                        </div>
                        <button
                          type="button"
                          className={`btn btn-sm fw-semibold ${
                            isCopied ? "btn-success" : "btn-outline-primary"
                          }`}
                          onClick={() => handleCopyCode(cls.join_code)}
                          title={t("teacher_classes.copy_code")}
                        >
                          {isCopied ? `✓ ${t("teacher_classes.code_copied")}` : `📋 ${t("teacher_classes.copy_code")}`}
                        </button>
                      </div>
                    </div>

                    {/* Enrolled Students Count */}
                    <div className="mb-4">
                      <span className="badge bg-light text-dark border px-2 py-1 small">
                        👥 {studentText}
                      </span>
                    </div>

                    {/* Action Buttons */}
                    <div className="mt-auto pt-3 border-top d-flex flex-column gap-2">
                      <Link
                        to={`/teacher/classes/${cls.id}`}
                        className="btn btn-primary btn-sm fw-bold w-100 text-center shadow-sm"
                      >
                        📊 {t("teacher_classes.view_dashboard_btn")}
                      </Link>
                      <div className="d-flex gap-2 w-100">
                        <button
                          type="button"
                          className="btn btn-outline-secondary btn-sm flex-grow-1 fw-semibold"
                          onClick={() => openEditModal(cls)}
                        >
                          ✏️ {t("teacher_classes.edit_btn")}
                        </button>

                        {cls.active ? (
                          <button
                            type="button"
                            className="btn btn-outline-secondary btn-sm fw-semibold"
                            onClick={() => setConfirmAction({ type: "archive", cls })}
                          >
                            📦 {t("teacher_classes.archive_btn")}
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="btn btn-outline-success btn-sm fw-semibold"
                            onClick={() => setConfirmAction({ type: "restore", cls })}
                          >
                            ♻️ {t("teacher_classes.restore_btn")}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CREATE CLASS MODAL */}
      {showCreateModal && (
        <div
          className="modal-backdrop-custom position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center p-3"
          style={{ backgroundColor: "rgba(0, 0, 0, 0.5)", zIndex: 1050 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-class-modal-title"
        >
          <div className="card shadow-lg border-0 w-100" style={{ maxWidth: "480px" }}>
            <div className="card-header bg-white border-0 pt-4 px-4 pb-0 d-flex justify-content-between align-items-center">
              <div>
                <h2 id="create-class-modal-title" className="h5 fw-bold mb-1">
                  {t("teacher_classes.create_modal_title")}
                </h2>
                <p className="text-muted small mb-0">{t("teacher_classes.create_modal_subtitle")}</p>
              </div>
              <button
                type="button"
                className="btn-close"
                onClick={() => !createSubmitting && setShowCreateModal(false)}
                disabled={createSubmitting}
                aria-label={t("teacher_classes.close")}
              />
            </div>

            <div className="card-body p-4">
              {createError && (
                <div className="alert alert-danger py-2 px-3 small mb-3" role="alert">
                  {createError}
                </div>
              )}

              <form onSubmit={handleCreateSubmit} noValidate>
                <div className="mb-3">
                  <label htmlFor="create-class-name" className="form-label fw-semibold small">
                    {t("teacher_classes.class_name_label")} *
                  </label>
                  <input
                    id="create-class-name"
                    type="text"
                    maxLength={80}
                    className="form-control"
                    placeholder={t("teacher_classes.class_name_placeholder")}
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    disabled={createSubmitting}
                    required
                    autoFocus
                  />
                </div>

                <div className="row g-2 mb-4">
                  <div className="col-6">
                    <label htmlFor="create-class-grade" className="form-label fw-semibold small">
                      {t("teacher_classes.grade_label")}
                    </label>
                    <input
                      id="create-class-grade"
                      type="text"
                      maxLength={10}
                      className="form-control"
                      placeholder={t("teacher_classes.grade_placeholder")}
                      value={createForm.grade}
                      onChange={(e) => setCreateForm({ ...createForm, grade: e.target.value })}
                      disabled={createSubmitting}
                    />
                  </div>
                  <div className="col-6">
                    <label htmlFor="create-class-section" className="form-label fw-semibold small">
                      {t("teacher_classes.section_label")}
                    </label>
                    <input
                      id="create-class-section"
                      type="text"
                      maxLength={10}
                      className="form-control"
                      placeholder={t("teacher_classes.section_placeholder")}
                      value={createForm.section}
                      onChange={(e) => setCreateForm({ ...createForm, section: e.target.value })}
                      disabled={createSubmitting}
                    />
                  </div>
                </div>

                <div className="d-flex justify-content-end gap-2 pt-2 border-top">
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setShowCreateModal(false)}
                    disabled={createSubmitting}
                  >
                    {t("common.cancel")}
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm fw-bold px-3"
                    disabled={createSubmitting}
                    id="btn-submit-create-class"
                  >
                    {createSubmitting ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                        {t("teacher_classes.submitting")}
                      </>
                    ) : (
                      t("teacher_classes.create_btn")
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* EDIT CLASS MODAL */}
      {editingClass && (
        <div
          className="modal-backdrop-custom position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center p-3"
          style={{ backgroundColor: "rgba(0, 0, 0, 0.5)", zIndex: 1050 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="edit-class-modal-title"
        >
          <div className="card shadow-lg border-0 w-100" style={{ maxWidth: "480px" }}>
            <div className="card-header bg-white border-0 pt-4 px-4 pb-0 d-flex justify-content-between align-items-center">
              <div>
                <h2 id="edit-class-modal-title" className="h5 fw-bold mb-1">
                  {t("teacher_classes.edit_modal_title")}
                </h2>
                <p className="text-muted small mb-0">
                  {editingClass.name} (Code: <span className="font-monospace fw-bold">{editingClass.join_code}</span>)
                </p>
              </div>
              <button
                type="button"
                className="btn-close"
                onClick={() => !editSubmitting && setEditingClass(null)}
                disabled={editSubmitting}
                aria-label={t("teacher_classes.close")}
              />
            </div>

            <div className="card-body p-4">
              {editError && (
                <div className="alert alert-danger py-2 px-3 small mb-3" role="alert">
                  {editError}
                </div>
              )}

              <form onSubmit={handleEditSubmit} noValidate>
                <div className="mb-3">
                  <label htmlFor="edit-class-name" className="form-label fw-semibold small">
                    {t("teacher_classes.class_name_label")} *
                  </label>
                  <input
                    id="edit-class-name"
                    type="text"
                    maxLength={80}
                    className="form-control"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    disabled={editSubmitting}
                    required
                  />
                </div>

                <div className="row g-2 mb-3">
                  <div className="col-6">
                    <label htmlFor="edit-class-grade" className="form-label fw-semibold small">
                      {t("teacher_classes.grade_label")}
                    </label>
                    <input
                      id="edit-class-grade"
                      type="text"
                      maxLength={10}
                      className="form-control"
                      value={editForm.grade}
                      onChange={(e) => setEditForm({ ...editForm, grade: e.target.value })}
                      disabled={editSubmitting}
                    />
                  </div>
                  <div className="col-6">
                    <label htmlFor="edit-class-section" className="form-label fw-semibold small">
                      {t("teacher_classes.section_label")}
                    </label>
                    <input
                      id="edit-class-section"
                      type="text"
                      maxLength={10}
                      className="form-control"
                      value={editForm.section}
                      onChange={(e) => setEditForm({ ...editForm, section: e.target.value })}
                      disabled={editSubmitting}
                    />
                  </div>
                </div>

                {/* Join Registration Switch */}
                <div className="form-check form-switch mb-3 p-3 bg-light rounded border">
                  <input
                    id="edit-join-enabled"
                    className="form-check-input ms-0 me-2"
                    type="checkbox"
                    role="switch"
                    checked={editForm.join_enabled}
                    onChange={(e) => setEditForm({ ...editForm, join_enabled: e.target.checked })}
                    disabled={editSubmitting}
                  />
                  <label htmlFor="edit-join-enabled" className="form-check-label fw-semibold small d-block">
                    {t("teacher_classes.join_enabled_label")}
                  </label>
                  <span className="text-muted small d-block">{t("teacher_classes.join_enabled_help")}</span>
                </div>

                {/* Rotate Join Code Option */}
                <div className="form-check p-3 bg-light rounded border mb-4">
                  <input
                    id="edit-rotate-code"
                    className="form-check-input ms-0 me-2"
                    type="checkbox"
                    checked={editForm.rotate_join_code}
                    onChange={(e) => setEditForm({ ...editForm, rotate_join_code: e.target.checked })}
                    disabled={editSubmitting}
                  />
                  <label htmlFor="edit-rotate-code" className="form-check-label fw-semibold small text-danger d-block">
                    ⚠️ {t("teacher_classes.rotate_code_label")}
                  </label>
                  <span className="text-muted small d-block">{t("teacher_classes.rotate_code_help")}</span>
                </div>

                <div className="d-flex justify-content-end gap-2 pt-2 border-top">
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setEditingClass(null)}
                    disabled={editSubmitting}
                  >
                    {t("common.cancel")}
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm fw-bold px-3"
                    disabled={editSubmitting}
                    id="btn-submit-edit-class"
                  >
                    {editSubmitting ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                        {t("teacher_classes.submitting")}
                      </>
                    ) : (
                      t("common.save")
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* CONFIRM ARCHIVE / RESTORE MODAL */}
      {confirmAction && (
        <div
          className="modal-backdrop-custom position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center p-3"
          style={{ backgroundColor: "rgba(0, 0, 0, 0.5)", zIndex: 1050 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-action-modal-title"
        >
          <div className="card shadow-lg border-0 w-100" style={{ maxWidth: "420px" }}>
            <div className="card-body p-4 text-center">
              <div className="fs-1 mb-2">{confirmAction.type === "archive" ? "📦" : "♻️"}</div>
              <h2 id="confirm-action-modal-title" className="h5 fw-bold mb-2">
                {confirmAction.type === "archive"
                  ? t("teacher_classes.confirm_archive_title")
                  : t("teacher_classes.confirm_restore_title")}
              </h2>
              <p className="text-muted small mb-4">
                {confirmAction.type === "archive"
                  ? t("teacher_classes.confirm_archive_msg", { name: confirmAction.cls.name })
                  : t("teacher_classes.confirm_restore_msg", { name: confirmAction.cls.name })}
              </p>

              <div className="d-flex justify-content-center gap-2">
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm px-3"
                  onClick={() => !confirmSubmitting && setConfirmAction(null)}
                  disabled={confirmSubmitting}
                >
                  {t("common.cancel")}
                </button>
                <button
                  type="button"
                  className={`btn btn-sm fw-bold px-4 ${
                    confirmAction.type === "archive" ? "btn-danger" : "btn-success"
                  }`}
                  onClick={handleConfirmAction}
                  disabled={confirmSubmitting}
                  id="btn-confirm-action"
                >
                  {confirmSubmitting ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />
                      {t("teacher_classes.submitting")}
                    </>
                  ) : (
                    t("teacher_classes.action_confirm")
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
