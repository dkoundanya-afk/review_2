"""python backend/manage.py load_data   -- import experiments, items, badges and the question bank.
Safe to run again: it updates in place."""
import json
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Badge, BankQuestion, Experiment, Item

GROUPS = {"CL": "chloride", "SO4": "sulphate", "CO3": "carbonate", "NO3": "nitrate"}


class Command(BaseCommand):
    help = "Load virtulab_data/ into the database"

    def handle(self, *a, **o):
        data = settings.REPO_ROOT / "virtulab_data"
        exp, _ = Experiment.objects.update_or_create(key="salt_analysis",
                                                     defaults={"subject": "chemistry", "title": "Salt Analysis"})
        qmap = json.loads((data / "quiz_map.json").read_text(encoding="utf-8"))
        for pos, (key, row) in enumerate(qmap.items()):
            Item.objects.update_or_create(key=key, defaults={
                "experiment": exp, "quiz_code": row["quiz_code"], "cation": row["cation"], "anion": row["anion"],
                "group_tag": GROUPS.get(row["anion"], ""), "formula": row["salt"], "name": row["name"], "position": pos})
        self.stdout.write(f"items: {Item.objects.count()}")

        for pos, b in enumerate(json.loads((data / "badges.json").read_text(encoding="utf-8"))):
            Badge.objects.update_or_create(key=b["key"], defaults={
                "name": b["name"], "description": b.get("description", ""), "rule_json": b["rule"], "position": pos})
        self.stdout.write(f"badges: {Badge.objects.count()}")

        bank, skipped = json.loads((data / "question_bank.json").read_text(encoding="utf-8")), 0
        for q in bank:
            if len(q["options"]) != 4 or q["correct_answer"] not in q["options"]:
                skipped += 1
                continue
            BankQuestion.objects.update_or_create(qid=q["id"], defaults={
                "experiment": q["experiment"], "subject": q["subject"], "item_key": q["item"], "radical": q["radical"],
                "test_type": q["test_type"], "difficulty": q["difficulty"], "lang": q.get("lang", "en"),
                "question": q["question"], "options": q["options"], "correct_answer": q["correct_answer"],
                "explanation": q.get("explanation", ""), "active": q.get("active", True)})
        self.stdout.write(f"bank questions: {BankQuestion.objects.count()} (skipped invalid: {skipped})")
