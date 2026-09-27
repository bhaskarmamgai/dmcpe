def common_error_message_format_for_client(msg, code):
    return {"message": msg, "code": code}

def common_response_message_format_for_client(msg, code):
    return {"message": msg, "code": code}

def validate_gstin(gstin):
    return True

def dbg_message(*args, **kwargs):
    print(*args, **kwargs)
