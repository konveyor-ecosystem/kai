import json

from aiohttp import web
from aiohttp.web_request import Request

from kai import llm_io_handler
from kai.routes.util import to_route

# TODO(@JonahSussman): Figure out proper pydantic model validation for this
# function


@to_route("get", "/ws/get_incident_solution")
async def get_ws_get_incident_solution(request: Request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    msg = await ws.receive()

    if msg.type == web.WSMsgType.TEXT:
        try:
            request_json = json.loads(msg.data)

            chunks = llm_io_handler.get_incident_solution(
                request.app["incident_store"],
                request.app["model_provider"],
                application_name=request_json["application_name"],
                ruleset_name=request_json["ruleset_name"],
                violation_name=request_json["violation_name"],
                incident_snip=request_json.get("incident_snip", ""),
                incident_vars=request_json["incident_variables"],
                file_name=request_json["file_name"],
                file_contents=request_json["file_contents"],
                line_number=request_json["line_number"],
                analysis_message=request_json.get("analysis_message", ""),
                stream=True,
            )

            for chunk in chunks:
                await ws.send_str(
                    json.dumps(
                        {
                            "content": chunk.content,
                        }
                    )
                )

        except json.JSONDecodeError:
            await ws.send_str(json.dumps({"error": "Received non-json data"}))

    elif msg.type == web.WSMsgType.ERROR:
        await ws.send_str(
            json.dumps({"error": f"Websocket closed with exception {ws.exception()}"})
        )
    else:
        await ws.send_str(json.dumps({"error": "Unsupported message type"}))

    await ws.close()

    return ws