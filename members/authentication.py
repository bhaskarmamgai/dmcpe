from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _

class AgencyJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that attaches the Member and Agency 
    to the request object upon successful authentication.
    """
    
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        
        user = self.get_user(validated_token)
        
        # Attach member and agency to request
        request.member = getattr(user, 'member', None)
        request.organization = getattr(user, 'organization', None)

        return user, validated_token

    def get_user(self, validated_token):
        """
        Returns the user model instance associated with the token,
        and attaches member/agency to the request if available.
        """
        user = super().get_user(validated_token)
        
        # Attach member and agency to user (and request if possible, but request isn't available here)
        # However, DRF authentication returns (user, token).
        # We can attach attributes to the user object itself.
        
        try:
            from members.models import Member
            member = Member.objects.select_related('organization').get(user=user)
            user.member = member
            user.organization = member.organization
        except Member.DoesNotExist:
            user.member = None
            user.organization = None
            
        return user
