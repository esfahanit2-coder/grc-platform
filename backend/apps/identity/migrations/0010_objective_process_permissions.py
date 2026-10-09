from django.db import migrations

def seed_objective_process_permissions(apps, schema_editor):
    Permission = apps.get_model("identity", "Permission")
    Role = apps.get_model("identity", "Role")
    RolePermission = apps.get_model("identity", "RolePermission")
    entries = [
        ("objective.view", "objective", "View objectives in assigned scope"),
        ("objective.manage", "objective", "Manage objectives in assigned scope"),
        ("process.view", "process", "View business processes in assigned scope"),
        ("process.manage", "process", "Manage business processes in assigned scope"),
    ]
    values = {}
    for code, module, description in entries:
        value, _ = Permission.objects.get_or_create(
            code=code, defaults={"module": module, "name": code.replace(".", " ").title(), "description": description}
        )
        values[code] = value
    for role in Role.objects.filter(is_system=True):
        granted = ["objective.view", "process.view"]
        if role.code in {"tenant_admin", "grc_manager"}:
            granted += ["objective.manage", "process.manage"]
        if role.code in {"tenant_admin", "grc_manager", "compliance_manager", "risk_manager", "control_owner", "auditor", "viewer"}:
            for code in granted:
                RolePermission.objects.get_or_create(role=role, permission=values[code])

class Migration(migrations.Migration):
    dependencies = [("identity", "0009_mfadevice_last_used_step")]
    operations = [migrations.RunPython(seed_objective_process_permissions, migrations.RunPython.noop)]
