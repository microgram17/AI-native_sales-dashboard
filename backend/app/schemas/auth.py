from pydantic import BaseModel


class CurrentUserContext(BaseModel):
    user_id: str
    display_name: str
    email: str
    allowed_supplier_codes: list[str]
