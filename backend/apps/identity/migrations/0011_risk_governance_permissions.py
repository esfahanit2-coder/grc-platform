from django.db import migrations


def seed_risk_governance_permissions(apps, schema_editor):
    Permission = apps.get_model("identity", "Permission")
    Role = apps.get_model("identity", "Role")
    RolePermission = apps.get_model("identity", "RolePermission")
    catalog = [
        ("risk.appetite.view", "View versioned risk appetite and tolerance"),
        ("risk.appetite.manage", "Draft and update risk appetite and tolerance"),
        ("risk.appetite.approve", "Approve risk appetite independently"),
        ("risk.accept.request", "Request acceptance of scoped evaluated risks"),
        ("risk.accept.approve", "Approve or reject another user risk acceptance"),
        ("risk.accept.override", "Approve a documented exception over tolerance"),
    ]
    objects = {}
    for code, description in catalog:
        permission, _ = Permission.objects.get_or_create(
            code=code, defaults={"module": "risk", "name": code.replace(".", " ").title(), "description": description},
        )
        objects[code] = permission
    grants = {
        "tenant_admin": list(objects),
        "grc_manager": ["risk.appetite.view", "risk.appetite.manage", "risk.appetite.approve", "risk.accept.request", "risk.accept.approve"],
        "risk_manager": ["risk.appetite.view", "risk.appetite.manage", "risk.accept.request"],
        "compliance_manager": ["risk.appetite.view"],
        "control_owner": ["risk.appetite.view", "risk.accept.request"],
        "auditor": ["risk.appetite.view"],
        "viewer": ["risk.appetite.view"],
    }
    for role in Role.objects.filter(is_system=True):
        for code in grants.get(role.code, []):
            RolePermission.objects.get_or_create(role=role, permission=objects[code])


class Migration(migrations.Migration):
    dependencies = [("identity", "0010_objective_process_permissions")]
    operations = [migrations.RunPython(seed_risk_governance_permissions, migrations.RunPython.noop)]
