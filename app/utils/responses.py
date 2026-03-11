from flask import jsonify

def api_response(success=True, status_code=200, message=None, data=None):
    response = {
        "success": success,
        "status_code": status_code,
        "message": message or ("Success" if success else "Error"),
    }
    if data is not None:
        response["data"] = data

    return jsonify(response), status_code