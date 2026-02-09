from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
import time

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/api/allotment':
            ip = self.get_client_ip(request)
            
            # Key for cache: rate_limit_IP
            key = f"rate_limit_{ip}"
            
            # Get current count
            # Using a list of timestamps for "Fixed time window" or "Sliding window"?
            # Requirement: "Fixed time window" (e.g. 10 req / 1 min?)
            # "Maximum 10 requests per IP" - Time window not specified in seconds, I'll assume 1 minute.
            # Let's use a simple counter with timeout if it doesn't exist.
            
            limit = 10
            window = 60 # seconds
            
            count = cache.get(key, 0)
            
            if count >= limit:
                return JsonResponse(
                    {'error': 'Rate limit exceeded. Try again later.'}, 
                    status=429
                )
            
            # Increment
            if count == 0:
                cache.set(key, 1, window)
            else:
                try:
                    cache.incr(key)
                except ValueError:
                    cache.set(key, 1, window) # Key might have expired just now
            
        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
