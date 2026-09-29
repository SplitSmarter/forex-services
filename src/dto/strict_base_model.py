from pydantic import BaseModel


class StrictBaseModel(BaseModel):
    """Base model with strict validation for all DTOs."""
    
    class Config:
        extra = "forbid"
        str_strip_whitespace = True