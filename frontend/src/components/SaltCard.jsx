/**
 * frontend/src/components/SaltCard.jsx
 * Displays a single salt item inside the 2-column dashboard grid.
 * Mobile-first: 2 columns at 360px width.
 * Meets Hard Rules:
 *  - Blue cation chip, Orange anion chip (ION DISPLAY TABLE)
 *  - Formulas with subscripts, ion charges with superscripts
 *  - Touch targets minimum 44px
 *  - High contrast and plain language
 */
import { useTranslation } from "react-i18next";
import { FormattedFormula, IonChip } from "./IonDisplay.jsx";

export default function SaltCard({
  item,
  onStartQuiz,
  onOpenResult,
  onResumeQuiz,
  isStarting = false,
}) {
  const { t } = useTranslation();

  const isLocked = item.status === "locked";
  const isUnlocked = item.status === "unlocked";
  const isCompleted = item.status === "completed";

  // Card click handling
  const handleCardClick = () => {
    if (isUnlocked) {
      if (item.attempt_id) {
        onResumeQuiz(item.attempt_id);
      } else if (item.redemption_id) {
        onStartQuiz(item.redemption_id, false);
      }
    } else if (isCompleted && item.attempt_id) {
      onOpenResult(item.attempt_id);
    }
  };

  return (
    <div
      className={`card salt-card h-100 d-flex flex-column ${
        isLocked
          ? "salt-card-locked"
          : isUnlocked
          ? "salt-card-unlocked cursor-pointer"
          : "salt-card-completed cursor-pointer"
      }`}
      onClick={handleCardClick}
      role={isLocked ? "article" : "button"}
      tabIndex={isLocked ? undefined : 0}
      onKeyDown={(e) => {
        if (!isLocked && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          handleCardClick();
        }
      }}
    >
      <div className="card-body p-2 p-sm-3 d-flex flex-column">
        {/* Header: Formula and Status Badge */}
        <div className="d-flex justify-content-between align-items-start mb-1">
          <div className="salt-formula fs-5 fw-bold text-dark">
            <FormattedFormula formula={item.formula} />
          </div>
          <div>
            {isLocked && (
              <span className="badge bg-secondary-subtle text-secondary border d-inline-flex align-items-center gap-1">
                <span aria-hidden="true">🔒</span>
                <span>{t("salt.locked")}</span>
              </span>
            )}
            {isUnlocked && (
              <span className="badge bg-primary text-white">
                {t("salt.quiz_ready")}
              </span>
            )}
            {isCompleted && (
              <span className="badge bg-success text-white">
                {item.score?.percent ?? 0}%
              </span>
            )}
          </div>
        </div>

        {/* Salt plain name */}
        <div className="salt-name mb-2" title={item.name}>
          {item.name}
        </div>

        {/* Ion Chips: Blue for cation, Orange for anion */}
        <div className="salt-chips mb-2">
          <IonChip ionKey={item.cation} type="cation" />
          <IonChip ionKey={item.anion} type="anion" />
        </div>

        {/* Small "lab data not available" note */}
        {item.no_lab_data && (
          <div className="salt-no-lab-data mb-2 text-center">
            <span className="badge bg-light text-secondary border extra-small">
              ⚠ {t("salt.no_lab_data")}
            </span>
          </div>
        )}

        {/* Actions spacer */}
        <div className="mt-auto pt-2">
          {isLocked && (
            <div className="text-muted extra-small text-center py-2">
              {t("salt.locked_hint")}
            </div>
          )}

          {isUnlocked && (
            <button
              type="button"
              className="btn btn-primary btn-sm w-100 min-touch-target fw-bold shadow-sm"
              disabled={isStarting}
              onClick={(e) => {
                e.stopPropagation();
                handleCardClick();
              }}
            >
              {isStarting
                ? t("quiz.starting")
                : item.attempt_id
                ? t("salt.resume_quiz")
                : t("salt.start_quiz")}
            </button>
          )}

          {isCompleted && (
            <div className="d-flex flex-column gap-1">
              <button
                type="button"
                className="btn btn-success btn-sm w-100 min-touch-target fw-bold"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenResult(item.attempt_id);
                }}
              >
                {t("salt.view_result")}
              </button>
              <button
                type="button"
                className="btn btn-outline-success btn-sm w-100 min-touch-target fw-medium"
                disabled={isStarting}
                onClick={(e) => {
                  e.stopPropagation();
                  onStartQuiz(item.redemption_id, true);
                }}
              >
                {isStarting ? t("quiz.starting") : t("salt.practice_again")}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
