import logging

logger = logging.getLogger(__name__)


class LogBadRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code != 200:
            logger.error(f"Bad Request, path {request.path}\n{getattr(response, 'data', '')}")

        return response
