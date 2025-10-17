# core/management/commands/setup_default_permissions.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.apps import apps

class Command(BaseCommand):
    help = "Create Requester, Reviewer, and Approver groups and assign permissions globally."

    def handle(self, *args, **options):
        groups = {
            "Requester": "can_request",
            "Reviewer": "can_review",
            "Approver": "can_approve",
        }

        for group_name, perm_codename in groups.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created group '{group_name}'"))

            # assign all permissions matching this codename across all models
            matched_perms = Permission.objects.filter(codename=perm_codename)
            if not matched_perms.exists():
                self.stdout.write(self.style.WARNING(f"No permissions found for {perm_codename} yet. Run `migrate` first."))

            group.permissions.add(*matched_perms)
            self.stdout.write(self.style.SUCCESS(f"Assigned {matched_perms.count()} '{perm_codename}' permissions to {group_name}"))

        self.stdout.write(self.style.SUCCESS("✅ Permission setup complete!"))
