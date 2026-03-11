from marshmallow import Schema
from marshmallow.fields import Int, Str, Bool, Raw, List, Nested


class ApiResponseSchema(Schema):
    success = Bool(required=True)
    status_code = Int(required=True)
    message = Str(required=True)
    data = Raw(required=False, allow_none=True)


def create_response_schema(schema, many=False, name=None):
    class ResponseSchema(ApiResponseSchema):
        data = (List(Nested(schema)) if many else Nested(schema))

    if name:
        ResponseSchema.__name__ = name
    return  ResponseSchema