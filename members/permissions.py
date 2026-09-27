from rest_framework import permissions
from members.models import Member


class IsOrganizationMember(permissions.BasePermission):
    """
    Permission to check if user has an associated Member profile.
    """
    message = "User must have an associated Member profile."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has a member profile
        return hasattr(request.user, 'member_profile')


class IsOrganizationOwner(permissions.BasePermission):
    """
    Permission to check if the object belongs to the user's organization.
    Object must have an 'organization' attribute.
    """
    message = "You do not have permission to access this resource."
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            member = request.user.member_profile
            
            # Check if object has organization attribute
            if hasattr(obj, 'organization'):
                return obj.organization == member.organization
            
            # Check if object has member attribute (for nested relationships)
            if hasattr(obj, 'member'):
                return obj.member.organization == member.organization
            
            return False
        except Member.DoesNotExist:
            return False
