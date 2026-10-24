"""python backend/manage.py create_teacher --email t@school.in --name "Ms Rao" --password ********"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from api.models import Profile


class Command(BaseCommand):
    help = "Create (or update the password of) a teacher account"

    def add_arguments(self, p):
        p.add_argument("--email", required=True)
        p.add_argument("--name", required=True)
        p.add_argument("--password", required=True)

    def handle(self, *a, **o):
        email, pw = o["email"].strip().lower(), o["password"]
        if "@" not in email or len(pw) < 8:
            raise CommandError("Need a valid email and a password of at least 8 characters")
        u, created = User.objects.get_or_create(username=email, defaults={"email": email})
        u.set_password(pw)
        u.save()
        Profile.objects.update_or_create(user=u, defaults={"role": "teacher", "display_name": o["name"], "pin_set": True})
        self.stdout.write(("created" if created else "updated") + f" teacher {email}")
