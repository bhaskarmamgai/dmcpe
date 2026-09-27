from rest_framework import serializers
from accounts.models import Posting, Journal
from organization.api.common.serializers import OrganizationBasicSerializer
from members.serializers import MemberSerializer
from wallet.api.private.serializers import WalletBasicSerializer


class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = ['id', 'type']


class PostingSerializer(serializers.ModelSerializer):
    organization = OrganizationBasicSerializer()
    member = MemberSerializer()
    wallet = WalletBasicSerializer()
    journal = JournalSerializer()

    class Meta:
        model = Posting
        fields = ['id', 'member', 'organization', 'wallet', 'journal', 'datetime', 'debit', 'credit', 'balance',
                  'description', 'created_at']
