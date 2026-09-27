from wallets.models import Wallet, WalletStatement


class WalletServices:
    from common.libraries import get_datetime_from_given_str_format, convert_ist_datetime_to_utc_timezone

    @staticmethod
    def create_wallet_for_organization(organization_id: int):
        obj, created = Wallet.objects.get_or_create(organization_id=organization_id,
                                                    defaults={'organization_id': organization_id})
        return obj, created

    @staticmethod
    def get_wallet_obj_by_organization_id(id: int):
        try:
            return Wallet.objects.get(organization_id=id)
        except Wallet.DoesNotExist:
            return None
        except Wallet.MultipleObjectsReturned:
            return None

    @staticmethod
    def get_wallet_id_by_organization_id(id: int):
        try:
            return (Wallet.objects.values('id').get(organization_id=id).get('id'))
        except Wallet.MultipleObjectsReturned:
            return None
        except Wallet.DoesNotExist:
            return None

    @staticmethod
    def get_wallet_object_by_id(id: int):
        return Wallet.objects.get(id=id)

    @staticmethod
    def update_wallet_by_id(wallet_id, **kwargs):
        wallet_queryset = Wallet.objects.filter(id=wallet_id).update(**kwargs)
        return wallet_queryset

    @staticmethod
    def get_wallet_object_by_code(wallet_code: str):
        try:
            return Wallet.objects.get(code=wallet_code)
        except Wallet.DoesNotExist:
            return None
        except Wallet.MultipleObjectsReturned:
            return None

    @staticmethod
    def get_wallet_obj_by_organization_code(code: str):
        return Wallet.objects.filter(organization__code=code)

    @staticmethod
    def get_wallet_object_for_update_by_wallet_id(wallet_id: int):
        try:
            return Wallet.objects.filter(id=wallet_id).select_for_update().get()
        except Wallet.DoesNotExist:
            return None
        except Wallet.MultipleObjectsReturned:
            return None

    @staticmethod
    def create_wallet_statement(**data):
        return WalletStatement.objects.create(**data)

    @staticmethod
    def get_wallet_postings_within_datetime_range_by_wallet_code(wallet_code, posting_start_date=None,
                                                                 posting_end_date=None, records_limit=None):
        wallet_obj = WalletServices.get_wallet_object_by_code(wallet_code)
        qs = wallet_obj.postings.filter(organization=wallet_obj.organization).order_by('created_at')
        if posting_start_date and posting_end_date:
            posting_start_datetime = WalletServices.get_datetime_from_given_str_format(posting_start_date)
            posting_end_datetime = WalletServices.get_datetime_from_given_str_format(posting_end_date) + timedelta(
                days=1)
            posting_start_date_utc = WalletServices.convert_ist_datetime_to_utc_timezone(posting_start_datetime)
            posting_end_date_utc = WalletServices.convert_ist_datetime_to_utc_timezone(posting_end_datetime)
            qs = qs.filter(datetime__gte=posting_start_date_utc, datetime__lt=posting_end_date_utc)
            if records_limit:
                qs = qs[0:records_limit]
        return qs
