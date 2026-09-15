import uuid


class CorrelationIdMiddleware:
    header_name = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw = request.META.get(self.header_name)
        try:
            request.correlation_id = uuid.UUID(raw) if raw else uuid.uuid4()
        except (TypeError, ValueError, AttributeError):
            request.correlation_id = uuid.uuid4()
        response = self.get_response(request)
        response["X-Request-ID"] = str(request.correlation_id)
        return response
