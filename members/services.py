from members.models import Member, Organization, BankAccount


class MemberServices:
    @staticmethod
    def get_member_details_from_member_id(member_id):
        return Member.objects.get(id=member_id)

    @staticmethod
    def get_member_data_from_member_id(member_id):
        return Member.objects.get(id=member_id)

    @staticmethod
    def get_member_queryset_from_member_ids(member_ids):
        return Member.objects.filter(id__in=member_ids)

    @staticmethod
    def get_member_bank_accounts_by_member_id(member_id):
        return BankAccount.objects.filter(organization__members__id=member_id).distinct()

    @staticmethod
    def get_members_bank_account_queryset_by_member_ids(member_ids):
        return BankAccount.objects.filter(organization__members__id__in=member_ids).distinct()

    @staticmethod
    def validate_members_organization_mandatory_fields_for_booking(member_organization_obj: Organization):
        error_message = ""
        admin_field_ids = []
        # Member Organization
        if not member_organization_obj.name:
            error_message += "Company Name Missing.<br />"
            admin_field_ids.append('#id_name')

        # organizationAddress
        if not member_organization_obj.addresses.last():
            error_message += "Address Details Missing.<br />"
            admin_field_ids.append('#id_addresses-0-line1')

        else:
            address = member_organization_obj.addresses.last()
            for field in ['address_line1', 'pincode', 'state']:
                if not getattr(address, field):
                    error_message += ("%s is missing in address. <br />" % field)
                    admin_field_ids.append('#id_addresses-0-line1')

        # MemberCompany Object
        if not hasattr(member_organization_obj, 'business_details'):
            error_message += "Company Details Missing.<br />"
            admin_field_ids.append('#id_business_details-0-primary_business')

        if hasattr(member_organization_obj, 'business_details') and (
                not getattr(member_organization_obj, 'business_details').gstin_number):
            error_message += "GSTIN Missing.<br />"
            admin_field_ids.append('#id_business_details-0-gstin_number')

        return error_message, admin_field_ids


class OrganizationServices:

    @staticmethod
    def get_organization_object_by_id(organization_id):
        return Organization.objects.get(id=organization_id)

    @staticmethod
    def get_member_organization_by_member_id(member_id):
        return MemberServices.get_member_data_from_member_id(member_id).organization

    @staticmethod
    def get_member_data_from_member_id(member_id):
        return MemberServices.get_member_data_from_member_id(member_id)

    @staticmethod
    def get_member_queryset_from_member_ids(member_ids):
        return MemberServices.get_member_queryset_from_member_ids(member_ids)

    @staticmethod
    def get_member_bank_accounts_by_member_id(member_id):
        return MemberServices.get_member_bank_accounts_by_member_id(member_id)

    @staticmethod
    def get_members_bank_account_queryset_by_member_ids(member_ids):
        return MemberServices.get_members_bank_account_queryset_by_member_ids(member_ids)

    @staticmethod
    def get_bank_accounts_by_organization_id(organization_id: int):
        return BankAccount.objects.filter(organization_id=organization_id, is_active=True, is_deleted=False)
