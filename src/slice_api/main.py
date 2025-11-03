from __future__ import annotations

import os
from fastapi import FastAPI, Path
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.requests import Request
from uuid import UUID, uuid4
import uvicorn

from models import (
    CreateSession,
    SessionId,
    SessionInfo,

)

app = FastAPI(
    title='Network Slice Booking',
    description='The Network Slice Booking (NSB) API provides programmable interface for developers to reserve a slice resource of a selected area within a period, and manage device access control as needed.\nFor specific details, please refer to [Network Slice Booking API Design.md](/documentation/API_documentation/Network_Slice_Booking_API_Design.md).\n\n# Introduction\n\nThis API allows the API consumer to book the availability of a session (also known as a "network slice"), specifying the service time, service area, and quality of service (QoS) profile.\nIt checks whether the requested QoS profile can be guaranteed for the indicated time and area, and, if so, it reserves the network slice accordingly, and monitors that the slice delivers the QoS profile. The latter process is known as Service Level Agreement (SLA) monitoring.\n\nThe API consumer can also retrieve information about an existing session or delete a session.\n\n# API functionality\n\nThe API provides the following functionality:\n- Create a new session (network slice), specifying the service time, service area, and QoS profile.\n- Retrieve information about an existing session, including the service time, service area, and QoS profile.\n- Delete an existing session.\n\n# Request Parameters Definition:\n* **serviceTime**: is defined by a start time and an end time, which indicates the period during which the network slice will be reserved.\n* **serviceArea**: can be defined as a circle or a polygon, allowing for flexible geographical coverage.\n* **sliceQosProfile**: includes parameters such as maximum number of devices, downstream and upstream rate per device, and packet delay budget.\n* **sessionId**: is a unique identifier for the session, which is returned when a session is created and used to retrieve or delete the session later.\n\n# Authorization and authentication\n\nThe "Camara Security and Interoperability Profile" provides details of how an API consumer requests an access token. Please refer to Identity and Consent Management (https://github.com/camaraproject/IdentityAndConsentManagement/) for the released version of the profile.\n\nThe specific authorization flows to be used will be agreed upon during the onboarding process, happening between the API consumer and the API provider, taking into account the declared purpose for accessing the API, whilst also being subject to the prevailing legal framework dictated by local legislation.\n\nIn cases where personal data is processed by the API and users can exercise their rights through mechanisms such as opt-in and/or opt-out, the use of three-legged access tokens is mandatory. This ensures that the API remains in compliance with privacy regulations, upholding the principles of transparency and user-centric privacy-by-design.\n\n# Additional CAMARA error responses\n\nThe list of error codes in this API specification is not exhaustive. Therefore the API specification may not document some non-mandatory error statuses as indicated in `CAMARA API Design Guide`.\n\nPlease refer to the `CAMARA_common.yaml` of the Commonalities Release associated to this API version for a complete list of error responses. The applicable Commonalities Release can be identified in the `API Readiness Checklist` document associated to this API version.\n\nAs a specific rule, error `501 - NOT_IMPLEMENTED` can be only a possible error response if it is explicitly documented in the API.\n',
    version='0.1.0-rc.1',
    license={
        'name': 'Apache 2.0',
        'url': 'https://www.apache.org/licenses/LICENSE-2.0.html',
    },
    servers=[
        {
            'url': '{apiRoot}/network-slice-booking/v0.1rc1',
            'variables': {
                'apiRoot': {
                    'default': 'http://localhost:8001',
                    'description': 'API root, defined by the service provider, e.g. `api.example.com` or `api.example.com/somepath`',
                }
            },
        }
    ],
)

# In-memory session store
_SESSIONS: dict[UUID, SessionInfo] = {}


def response(status_code: int, code: str, message: str) -> JSONResponse:
    """Helper to build error responses matching the generated error models."""
    payload = {
        "status": status_code,
        "code": code,
        "message": message,
    }
    return JSONResponse(status_code=status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a consistent 400 payload when validation fails (e.g., invalid UUID).

    Specifically customize the message when the path parameter `sessionId` is not
    a valid UUID, otherwise fall back to a generic invalid-parameters message.
    """
    try:
        for err in exc.errors():
            loc = err.get("loc", [])
            if len(loc) >= 2 and loc[0] == "path" and loc[1] == "sessionId":
                return response(
                    status_code=400,
                    code="INVALID_ARGUMENT",
                    message="sessionId must be a valid UUID.",
                )
    except Exception:
        # If anything unexpected happens while inspecting errors, still return a 400
        pass

    # Default validation error response
    return response(
        status_code=400,
        code="INVALID_ARGUMENT",
        message="Invalid request parameters.",
    )


@app.post(
    '/sessions',
    response_model=None,
    tags=['Network Slice Booking Sessions'],
)
def create_session(body: CreateSession):
    """
    Creates a new session
    """
    # Basic validation examples to demonstrate error responses
    # Validate serviceTime consistency if provided
    if body.serviceTime and body.serviceTime.endDate and body.serviceTime.startDate:
        if body.serviceTime.endDate <= body.serviceTime.startDate:
            return response(
                status_code=400,
                code='OUT_OF_RANGE',
                message='endDate must be greater than startDate.',
            )

    if len(_SESSIONS) >= 1000:
        return response(
            status_code=429,
            code='TOO_MANY_REQUESTS',
            message='Session quota exceeded. Try again later.',
        )

    # Create the session
    sid = uuid4()
    session_info = SessionInfo(
        serviceTime=body.serviceTime,
        serviceArea=body.serviceArea,
        sliceQosProfile=body.sliceQosProfile,
        sessionId=SessionId(session_id=sid),
    )
    _SESSIONS[sid] = session_info

    return response(
            status_code=201,
            code='SUCCESS',
            message=session_info.json(),
        )


@app.delete(
    '/sessions/{sessionId}',
    response_model=None,
    tags=['Network Slice Booking Sessions'],
)
def delete_session(sessionId: UUID = Path(...)):
    """
    Delete a NSB session
    """
    if sessionId not in _SESSIONS:
        return response(
            status_code=404,
            code='NOT_FOUND',
            message=f'Session {sessionId} was not found.',
        )

    del _SESSIONS[sessionId]
    
    return response(
            status_code=410,
            code='DELETED',
            message=f"Session Id {sessionId} successfully deleted."
        )


@app.get(
    '/sessions/{sessionId}',
    response_model=SessionInfo,
    tags=['Network Slice Booking Sessions'],
)
def get_session(sessionId: UUID = Path(...)):
    """
    Get NSB session information
    """
    session = _SESSIONS.get(sessionId)
    if not session:
        return response(
            status_code=404,
            code='NOT_FOUND',
            message=f'Session {sessionId} was not found.',
        )
    return session

if __name__ == "__main__":
    # If executed as a script, reference the local module path
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run("app.main:app" if __package__ else "main:app", host='127.0.0.1', port=port, reload=True)