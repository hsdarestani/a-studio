from django import template

register = template.Library()


@register.simple_tag
def recent_store_submissions(project, limit=3):
    return project.store_submissions.order_by("-created_at")[:limit]
