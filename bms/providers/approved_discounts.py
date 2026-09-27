from bms.models.approved_discount import ApprovedDiscount

def get_approved_discounts_object_from_approved_discounts_id(approved_discount_id):
    try:
        return ApprovedDiscount.objects.get(id=approved_discount_id)
    except:
        return None


def create_approved_discount(data):
    return ApprovedDiscount.objects.create(**data)
