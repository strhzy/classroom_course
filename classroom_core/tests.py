import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from classroom_core.models import (
    Assignment,
    AssignmentFile,
    AssignmentQuizOption,
    AssignmentQuizQuestion,
    AssignmentQuizAttempt,
    AssignmentSubmission,
    Course,
)
from file_manager.models import File


class AssignmentTypeTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="pass")
        self.student = User.objects.create_user(username="student", password="pass")
        self.teacher.profile.role = "teacher"
        self.teacher.profile.save()
        self.student.profile.role = "student"
        self.student.profile.save()
        self.course = Course.objects.create(
            title="Course",
            description="desc",
            instructor=self.teacher,
            status="active",
        )
        self.course.students.add(self.student)

    def test_assignment_defaults_to_file_upload(self):
        assignment = Assignment.objects.create(
            course=self.course,
            title="A1",
            description="d",
            due_date=timezone.now() + timedelta(days=1),
            status="published",
        )
        self.assertEqual(assignment.assignment_type, "file_upload")
        self.assertEqual(assignment.quiz_mode, "single")

    def test_quiz_submit_creates_attempt_and_autogrades(self):
        assignment = Assignment.objects.create(
            course=self.course,
            title="Quiz",
            description="d",
            due_date=timezone.now() + timedelta(days=1),
            status="published",
            assignment_type="quiz",
            quiz_mode="single",
        )
        question = AssignmentQuizQuestion.objects.create(assignment=assignment, question_text="2+2?")
        correct = AssignmentQuizOption.objects.create(question=question, option_text="4", is_correct=True)
        AssignmentQuizOption.objects.create(question=question, option_text="5", is_correct=False)

        self.client.login(username="student", password="pass")
        response = self.client.post(
            reverse("classroom_core:assignment_quiz_submit", args=[assignment.id]),
            {f"question_{question.id}": str(correct.id)},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        attempt = AssignmentQuizAttempt.objects.filter(assignment=assignment, student=self.student).first()
        self.assertIsNotNone(attempt)
        self.assertTrue(attempt.is_correct)
        self.assertEqual(attempt.correct_answers, 1)
        self.assertEqual(attempt.total_questions, 1)
        submission = AssignmentSubmission.objects.filter(assignment=assignment, student=self.student).first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.score, assignment.max_points)

    def test_file_assignment_upload_blocked_after_deadline(self):
        assignment = Assignment.objects.create(
            course=self.course,
            title="File Assignment",
            description="d",
            due_date=timezone.now() - timedelta(days=1),
            status="published",
            assignment_type="file_upload",
        )
        file_obj = File.objects.create(
            title="doc.txt",
            uploaded_by=self.student,
            visibility="private",
            file_size=10,
            storage_provider="local",
        )
        self.client.login(username="student", password="pass")
        response = self.client.post(
            reverse("classroom_core:assignment_submit", args=[assignment.id]),
            {"storage_file": str(file_obj.id), "attachment_description": "late"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AssignmentFile.objects.filter(assignment=assignment, student=self.student).exists())

    def test_quiz_payload_from_assignment_form_is_saved(self):
        self.client.login(username="teacher", password="pass")
        payload = [
            {
                "text": "Столица Франции?",
                "options": [
                    {"text": "Париж", "is_correct": True},
                    {"text": "Лион", "is_correct": False},
                ],
            }
        ]
        response = self.client.post(
            reverse("classroom_core:assignment_create", args=[self.course.id]),
            {
                "title": "Quiz Payload",
                "description": "desc",
                "due_date": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                "assignment_type": "quiz",
                "quiz_mode": "single",
                "max_points": 100,
                "passing_score": 50,
                "status": "published",
                "quiz_payload": json.dumps(payload, ensure_ascii=False),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        assignment = Assignment.objects.filter(course=self.course, title="Quiz Payload").first()
        self.assertIsNotNone(assignment)
        question = assignment.quiz_questions.first()
        self.assertIsNotNone(question)
        self.assertEqual(question.options.count(), 2)
        self.assertTrue(question.options.filter(option_text="Париж", is_correct=True).exists())
