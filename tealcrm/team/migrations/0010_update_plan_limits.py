from django.db import migrations


PLAN_LIMITS = (
    {
        'name': 'Starter',
        'aliases': ('Starter', 'Basic'),
        'defaults': {
            'max_members': 1,
            'max_leads': 10,
            'max_clients': 5,
            'max_sessions_per_month': 10,
        },
    },
    {
        'name': 'Professional',
        'aliases': ('Professional',),
        'defaults': {
            'max_members': 5,
            'max_leads': 500,
            'max_clients': 200,
            'max_sessions_per_month': None,
        },
    },
    {
        'name': 'Business',
        'aliases': ('Business', 'Premium'),
        'defaults': {
            'max_members': 15,
            'max_leads': None,
            'max_clients': None,
            'max_sessions_per_month': None,
        },
    },
)


def update_plan_limits(apps, schema_editor):
    Plan = apps.get_model('team', 'Plan')

    for spec in PLAN_LIMITS:
        for plan in Plan.objects.filter(name__in=spec['aliases']):
            for field_name, value in spec['defaults'].items():
                setattr(plan, field_name, value)
            plan.save(update_fields=list(spec['defaults'].keys()))


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0009_seed_default_plan_limits'),
    ]

    operations = [
        migrations.RunPython(update_plan_limits, migrations.RunPython.noop),
    ]
