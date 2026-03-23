from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.selectors import get_booking_history
from apps.audit.serializers import BookingHistorySerializer

from .exceptions import BookingConflictError, BookingValidationError
from .filters import BookingFilter
from .selectors import can_manage_all_bookings, get_bookings_for_user
from .serializers import (
    BookingCreateSerializer,
    BookingReadSerializer,
    BookingUpdateSerializer,
)
from .services import cancel_booking, create_booking, update_booking


class BookingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]

    filterset_class = BookingFilter

    ordering_fields = ("start_at", "end_at", "created_at", "status")

    ordering = ("-start_at",)

    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return get_bookings_for_user(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer

        if self.action == "partial_update":
            return BookingUpdateSerializer

        if self.action == "history":
            return BookingHistorySerializer

        return BookingReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = dict(serializer.validated_data)

        target_user = validated_data.pop("user", None)

        if target_user is None:
            target_user = request.user

        elif target_user != request.user and not can_manage_all_bookings(request.user):
            raise PermissionDenied("You cannot create bookings for another user.")

        try:
            booking = create_booking(
                user=target_user, changed_by=request.user, **validated_data
            )

        except BookingConflictError as exc:
            return self._domain_error_response(exc, status.HTTP_409_CONFLICT)
        except BookingValidationError as exc:
            return self._domain_error_response(exc, status.HTTP_400_BAD_REQUEST)

        output_serializer = BookingReadSerializer(
            booking, context=self.get_serializer_context()
        )

        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):

        booking = self.get_object()

        serializer = self.get_serializer(data=request.data, partial=True)

        serializer.is_valid(raise_exception=True)

        try:
            booking = update_booking(
                booking=booking,
                changed_by=request.user,
                **serializer.validated_data,
            )

        except BookingConflictError as exc:
            return self._domain_error_response(exc, status.HTTP_409_CONFLICT)
        except BookingValidationError as exc:
            return self._domain_error_response(exc, status.HTTP_400_BAD_REQUEST)

        output_serializer = BookingReadSerializer(
            booking, context=self.get_serializer_context()
        )

        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()

        try:
            booking = cancel_booking(booking=booking, changed_by=request.user)

        except BookingValidationError as exc:
            return self._domain_error_response(exc, status.HTTP_400_BAD_REQUEST)

        output_serializer = BookingReadSerializer(
            booking, context=self.get_serializer_context()
        )

        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def _domain_error_response(
        exc,
        response_status,
    ):
        return Response(
            {"detail": exc.message, "code": exc.code},
            status=response_status,
        )

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        booking = self.get_object()

        queryset = get_booking_history(booking=booking)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)

            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
