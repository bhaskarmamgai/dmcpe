from bms.providers import approved_discounts

def get_approved_discounts_object_from_approved_discounts_id(approved_discount_id):
    return approved_discounts.get_approved_discounts_object_from_approved_discounts_id(approved_discount_id)

def create_approved_discount(data):
    return approved_discounts.create_approved_discount(data=data)