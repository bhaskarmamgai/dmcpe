from members.services import MemberServices as members


def get_member_obj_by_id(member_id):
    return members.get_member_data_from_member_id(member_id)


def get_member_queryset_from_member_ids(member_ids):
    return members.get_member_queryset_from_member_ids(member_ids)


def get_member_bank_accounts_by_member_id(member_id:int):
    return members.get_member_bank_accounts_by_member_id(member_id)


def get_members_bank_account_queryset_by_member_ids(member_ids):
    return members.get_members_bank_account_queryset_by_member_ids(member_ids)