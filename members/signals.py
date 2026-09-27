from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from members.models import Member


@receiver(post_save, sender=Member)
def post_save_member(sender, instance, created, **kwargs):
    """
    Create User for Member AFTER transaction commit
    """
    if not created:
        return

    def create_user_after_commit():
        from users.models import User

        # Safety: Member may already be linked
        if instance.user_id:
            return

        user, _ = User.objects.get_or_create(
            email=instance.email,
            defaults={
                "role": "member",
                "username": instance.email,
                "email": instance.email,
            },
        )

        # Use queryset update to avoid triggering signals again
        Member.objects.filter(pk=instance.pk).update(user=user)

        print(f"✅ User {user.email} linked to Member {instance.id}")

    transaction.on_commit(create_user_after_commit)
