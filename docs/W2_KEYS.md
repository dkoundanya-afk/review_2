# Keys the server sends (translate these in en.json; unknown key -> hide it)

points.lines[].reason  ->  correct_bank_easy | correct_bank_medium | correct_bank_hard | correct_dynamic | quiz_completion | lab_flawless_bonus
  (the same reasons appear in /api/history ledger[].reason)

insights[].key  ->  insight.mis_order_wrong | insight.mis_reagent_excess | insight.mis_skipped_flame | insight.mis_skipped_confirmatory |
  insight.mis_skipped_dissolve | insight.mis_repeated_same_test | insight.mis_wrong_reagent_for_goal | insight.mis_wrong_submission |
  insight.lab_flawless | insight.lab_attempts {att} | insight.wrong_guess {cat, an}   (cat/an are ion ids like CU, SO4: show with the ION DISPLAY TABLE)

feedback[].key  ->  feedback.excellent {percent} | feedback.good {percent} | feedback.keep_practising {percent} | feedback.review_basics {percent} |
  feedback.weak_topic {kind, tag} | feedback.no_lab_data | feedback.practice

weak_topics[]: {kind:"test_type"|"radical", tag, wrong, total}.  For kind "test_type" show the tag with underscores as spaces (flame, gas test,
  group reagent, dilute acid ...). For kind "radical" the tag is an ion such as "Cu2+" or "SO4 2-": show it with sub/superscripts.

Extra error codes (map each to a translated message): not_found, invalid_answer, already_submitted, already_graded, practice_after_graded, not_submitted.
