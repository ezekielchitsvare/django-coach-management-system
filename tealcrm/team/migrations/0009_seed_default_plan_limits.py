from django.db import migrations


PLAN_SPECS = (
    {
        'name': 'Starter',
        'aliases': ('Starter', 'Basic'),
        'defaults': {
            'setup_fee': 0,
            'monthly_price': 0,
            'description': 'Best for solo coaches and very small teams getting started.',
            'max_members': 2,
            'max_leads': 25,
            'max_clients': 15,
            'max_sessions_per_month': 20,
            'has_analytics': False,
            'has_team_roles': False,
            'has_email_reminders': False,
            'has_advanced_analytics': False,
            'has_export_tools': False,
        },
    },
    {
        'name': 'Professional',
        'aliases': ('Professional',),
        'defaults': {
            'setup_fee': 0,
            'monthly_price': 19,
            'description': 'For growing coaching teams that need analytics, roles, and reminders.',
            'max_members': 5,
            'max_leads': 500,
            'max_clients': 200,
            'max_sessions_per_month': None,
            'has_analytics': True,
            'has_team_roles': True,
            'has_email_reminders': True,
            'has_advanced_analytics': False,
            'has_export_tools': False,
        },
    },
    {
        'name': 'Business',
        'aliases': ('Business', 'Premium'),
        'defaults': {
            'setup_fee': 0,
            'monthly_price': 49,
            'description': 'For established businesses that need unlimited scale and advanced tools.',
            'max_members': 15,
            'max_leads': None,
            'max_clients': None,
            'max_sessions_per_month': None,
            'has_analytics': True,
            'has_team_roles': True,
            'has_email_reminders': True,
            'has_advanced_analytics': True,
            'has_export_tools': True,
        },
    },
)


def seed_default_plans(apps, schema_editor):
    Plan = apps.get_model('team', 'Plan')
    Team = apps.get_model('team', 'Team')

    for spec in PLAN_SPECS:
        matching_plans = list(Plan.objects.filter(name__in=spec['aliases']).order_by('id'))
        primary_plan = None

        for plan in matching_plans:
            if plan.name == spec['name']:
                primary_plan = plan
                break

        if primary_plan is None and matching_plans:
            primary_plan = matching_plans[0]

        if primary_plan is None:
            primary_plan = Plan.objects.create(name=spec['name'], **spec['defaults'])
        else:
            primary_plan.name = spec['name']
            for field_name, value in spec['defaults'].items():
                setattr(primary_plan, field_name, value)
            primary_plan.save()

        for duplicate_plan in matching_plans:
            if duplicate_plan.pk == primary_plan.pk:
                continue

            Team.objects.filter(plan_id=duplicate_plan.pk).update(plan_id=primary_plan.pk)
            duplicate_plan.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0008_plan_has_advanced_analytics_plan_has_analytics_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_default_plans, migrations.RunPython.noop),
    ]
