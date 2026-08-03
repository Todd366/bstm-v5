import uuid


def generate_id(
    prefix
):

    return (
        f"{prefix}-"
        f"{uuid.uuid4().hex}"
    )
