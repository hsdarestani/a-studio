from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import AuditEvent, Conversation, Membership, Message, Organization, Project, StoreSubmission
from .services.ai import initial_spec
from .tasks import notify_store_submission

User = get_user_model()


class WorkflowUXTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner-workflow@example.com", email="owner-workflow@example.com", password="safe-password-123", first_name="Max", last_name="Mustermann")
        self.org = Organization.objects.create(name="Workflow GmbH", owner=self.user, credits=20)
        Membership.objects.create(organization=self.org, user=self.user, role="owner")
        self.project = Project.objects.create(organization=self.org, created_by=self.user, name="Workflow App", business_type="Retail", description="Workflow testing", language="de", app_spec=initial_spec("Workflow App", "Retail", "Workflow testing", "de"))
        self.conversation = Conversation.objects.create(project=self.project)
        self.client.force_login(self.user)

    @patch("core.workflow_views.process_chat_message.delay")
    def test_chat_submit_creates_resumable_queued_build(self, delay):
        delay.return_value = Mock(id="celery-123")
        response = self.client.post(reverse("chat_submit", args=[self.project.id]), {"message": "Make the hero premium"})
        self.assertEqual(response.status_code, 200)
        assistant = self.conversation.messages.filter(role="assistant").get()
        self.assertEqual(assistant.status, "queued")
        self.assertEqual(assistant.metadata["progress"]["stage"], "queued")
        self.assertEqual(assistant.metadata["progress"]["percent"], 5)
        self.assertEqual(assistant.task_id, "celery-123")

    @patch("core.workflow_views.process_chat_message.delay")
    def test_second_chat_request_is_rejected_while_build_active(self, delay):
        Message.objects.create(conversation=self.conversation, role="assistant", content="Running", status="working", metadata={"progress": {"stage": "building", "percent": 60}})
        before = self.conversation.messages.count()
        response = self.client.post(reverse("chat_submit", args=[self.project.id]), {"message": "Duplicate request"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.conversation.messages.count(), before)
        delay.assert_not_called()

    @patch("core.workflow_views.notify_store_submission.delay")
    def test_store_request_is_persistent_and_notification_is_queued(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("request_store_submission", args=[self.project.id]), {"platform": "both", "notes": "Please review both stores"})
        submission = self.project.store_submissions.get()
        self.assertRedirects(response, reverse("store_submissions", args=[self.project.id]), fetch_redirect_response=False)
        self.assertEqual(submission.status, "requested")
        self.assertEqual(submission.notes, "Please review both stores")
        delay.assert_called_once_with(str(submission.id))
        page = self.client.get(reverse("store_submissions", args=[self.project.id]))
        self.assertContains(page, "Both stores")
        self.assertContains(page, str(submission.id)[:8])

    @patch("core.workflow_views.notify_store_submission.delay")
    def test_duplicate_active_store_request_is_not_created(self, delay):
        StoreSubmission.objects.create(project=self.project, requested_by=self.user, platform="both", status="eligibility")
        response = self.client.post(reverse("request_store_submission", args=[self.project.id]), {"platform": "both"})
        self.assertEqual(self.project.store_submissions.count(), 1)
        self.assertRedirects(response, reverse("store_submissions", args=[self.project.id]), fetch_redirect_response=False)
        delay.assert_not_called()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="A+ Studio <app@aplus-solution.de>", BILLING_CONTACT_EMAIL="ops@example.com", APP_PUBLIC_URL="https://studio.example.com")
class StoreNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="store-user@example.com", email="store-user@example.com", password="safe-password-123")
        self.org = Organization.objects.create(name="Store GmbH", owner=self.user)
        Membership.objects.create(organization=self.org, user=self.user, role="owner")
        self.project = Project.objects.create(organization=self.org, created_by=self.user, name="Store App", business_type="Retail", description="Store publishing", language="de", app_spec=initial_spec("Store App", "Retail", "Store publishing", "de"))
        self.submission = StoreSubmission.objects.create(project=self.project, requested_by=self.user, platform="both", status="requested")

    def test_store_request_sends_team_and_customer_email_and_audit_event(self):
        result = notify_store_submission.run(str(self.submission.id))
        self.assertEqual(result["status"], "sent")
        self.assertEqual(len(mail.outbox), 2)
        recipients = {recipient for message in mail.outbox for recipient in message.to}
        self.assertIn("ops@example.com", recipients)
        self.assertIn("store-user@example.com", recipients)
        self.assertTrue(AuditEvent.objects.filter(action="store_submission_notification_sent", project=self.project).exists())
