"""W2 HTTP layer for the quiz (thin)."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .auth import IsStudent
from .errors import ApiError
from .models import QuizAttempt
from . import quiz


def _own(request, pk) -> QuizAttempt:
    att = QuizAttempt.objects.select_related("redemption__item", "student").filter(pk=pk, student=request.user).first()
    if att is None:
        raise ApiError(404, "not_found")
    return att


@api_view(["POST"])
@permission_classes([IsStudent])
def quiz_start(request):
    att = quiz.start_attempt(request.user, request.data.get("redemption_id"), bool(request.data.get("practice")))
    return Response({"attempt_id": att.id}, status=201)


@api_view(["GET"])
@permission_classes([IsStudent])
def quiz_detail(request, pk):
    return Response(quiz.quiz_json(_own(request, pk)))


@api_view(["PUT"])
@permission_classes([IsStudent])
def quiz_answers(request, pk):
    return Response({"saved": quiz.save_answers(_own(request, pk), request.data.get("answers"))})


@api_view(["POST"])
@permission_classes([IsStudent])
def quiz_submit(request, pk):
    att = _own(request, pk)
    quiz.submit_attempt(att, request.data.get("answers"))
    return Response(quiz.build_result(_own(request, pk)))


@api_view(["GET"])
@permission_classes([IsStudent])
def quiz_result(request, pk):
    return Response(quiz.build_result(_own(request, pk)))


@api_view(["GET"])
@permission_classes([IsStudent])
def history(request):
    return Response(quiz.history_for(request.user))
