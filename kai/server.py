#!/usr/bin/python3

# FIXME: This code should live in 'kai-service' but I couldn't get it to import
# the required `kai` modules. Someone smarter than me may be able to fix this.
# For now, I just copied this code wholesale. - jsussman

"""This module is intended to facilitate using Konveyor with LLMs."""

import json
import os
import warnings
from os import listdir
from os.path import isfile, join

import aiohttp
import jsonschema
import yaml
from aiohttp import web
from aiohttp.web_request import Request
from incident_store_advanced import Application, EmbeddingNone, PSQLIncidentStore
from model_provider import IBMGraniteModel, ModelProvider
from prompt_builder import PromptBuilder
from report import Report

# TODO: Make openapi spec for everything

# TODO: Repo lives both on client and on server. Determine either A) Best way to
# rectify differences or B) Only have the code on one and pass stuff between
# each other
# - can be solved by getting last common commits and then applying a git diff in
#   the same manner as `git stash apply`


routes = web.RouteTableDef()

JSONSCHEMA_DIR = os.path.join(
    os.path.dirname(__file__),
    "data/jsonschema/",
)


def load_config():
    """Load the configuration from a yaml conf file."""
    config_prefix = "/usr/local/etc"
    if os.environ.get("KAI_CONFIG_PREFIX"):
        config_prefix = os.environ.get("KAI_CONFIG_PREFIX")

    config_dir = "kai.conf.d"
    model_dir = os.path.join(config_prefix, config_dir)
    files = [f for f in listdir(model_dir) if isfile(join(model_dir, f))]
    model_templates = {}
    for f in files:
        filename, file_extension = os.path.splitext(f)
        with open(join(model_dir, f), encoding="utf-8") as reader:
            try:
                model = reader.read()
                model_templates[filename] = model
            except yaml.YAMLError as exc:
                print(exc)
                return None
    return {"model_templates": model_templates}


def load_templates():
    """Get model templates from the loaded configuration."""
    return load_config()["model_templates"]


def load_template(model_name):
    """Loads the requested template."""
    model_templates = load_templates()
    if model_name in model_templates:
        return model_templates[model_name]

    warnings.warn(
        "Warning: Model not found, using first available model.",
        stacklevel=5,
    )
    return list(model_templates.items())[0][1]


@routes.post("/generate_prompt")
async def generate_prompt(request):
    """Generates a prompt based on input using the specified template."""
    try:
        data = await request.json()

        language = data.get("language", "")
        issue_description = data.get("issue_description", "")
        example_original_code = data.get("example_original_code", "")
        example_solved_code = data.get("example_solved_code", "")
        current_original_code = data.get("current_original_code", "")
        model_template = data.get("model_template", "")

        if model_template == "":
            warnings.warn(
                "Model template not specified. For best results specify a model template.",
                stacklevel=5,
            )

        response = load_template(model_template).format(
            language=language,
            issue_description=issue_description,
            example_original_code=example_original_code,
            example_solved_code=example_solved_code,
            current_original_code=current_original_code,
            model_template=model_template,
        )

        warnings.resetwarnings()
        return web.json_response({"generated_prompt": response})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@routes.route("*", "/proxy")
async def proxy_handler(request):
    """Proxies a streaming request to an LLM."""
    upstream_url = request.query.get("upstream_url")

    if not upstream_url:
        return web.Response(
            status=400, text="Missing 'upstream_url' parameter in the request"
        )

    headers = {}
    if request.headers.get("Authorization"):
        headers.update({"Authorization": request.headers.get("Authorization")})
    if request.headers.get("Content-Type"):
        headers.update({"Content-Type": request.headers.get("Content-Type")})
    method = request.method
    data = await request.read()

    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method, upstream_url, headers=headers, data=data
            ) as upstream_response:
                if "chunked" in upstream_response.headers.get("Transfer-Encoding", ""):
                    response = web.StreamResponse()
                    await response.prepare(request)

                    async for data in upstream_response.content.iter_any():
                        await response.write(data)

                    await response.write_eof()
                    return response

                return web.Response(
                    status=upstream_response.status,
                    text=await upstream_response.text(),
                    headers=upstream_response.headers,
                )
        except aiohttp.ClientError as e:
            return web.Response(
                status=500, text=f"Error connecting to upstream service: {str(e)}"
            )


async def run_analysis_report():
    pass


@routes.post("/dummy_json_request")
async def post_dummy_json_request(request: Request):
    print(f"post_dummy_json_request recv'd: {request}")

    request_json: dict = await request.json()

    return web.json_response({"feeling": "OK!", "recv": request_json})


@routes.post("/load_analysis_report")
async def post_load_analysis_report(request: Request):
    schema: dict = json.loads(
        open(os.path.join(JSONSCHEMA_DIR, "post_load_analysis_report.json")).read()
    )
    request_json: dict = await request.json()

    try:
        jsonschema.validate(instance=request_json, schema=schema)
    except jsonschema.ValidationError as err:
        raise web.HTTPUnprocessableEntity(text=f"{err}") from err

    request_json["application"].setdefault("application_id")

    application = Application(**request_json["application"])
    path_to_report: str = request_json["path_to_report"]
    report = Report(path_to_report)

    count = incident_store.insert_and_update_from_report(application, report)

    return web.json_response(
        {
            "number_new_incidents": count[0],
            "number_unsolved_incidents": count[1],
            "number_solved_incidents": count[2],
        }
    )


@routes.post("/change_model")
async def post_change_model(request: Request):
    pass


def get_incident_solution(request_json: dict, stream: bool = False):
    schema: dict = json.loads(
        open(os.path.join(JSONSCHEMA_DIR, "post_get_incident_solution.json")).read()
    )

    try:
        jsonschema.validate(instance=request_json, schema=schema)
    except jsonschema.ValidationError as err:
        raise web.HTTPUnprocessableEntity(text=f"{err}") from err

    application_name: str = request_json["application_name"]
    application_name = application_name  # NOTE: To please trunk error, remove me
    ruleset_name: str = request_json["ruleset_name"]
    violation_name: str = request_json["violation_name"]
    incident_snip: str = request_json["incident_snip"]
    incident_vars: dict = request_json["incident_variables"]
    file_name: str = request_json["file_name"]
    file_contents: str = request_json["file_contents"]
    line_number: int = request_json["line_number"]
    analysis_message: str = request_json.get("analysis_message", "")

    # Gather context
    # First, let's see if there's an "exact" match

    solved_incident, match_type = incident_store.get_fuzzy_similar_incident(
        violation_name, ruleset_name, incident_snip, incident_vars
    )

    if not isinstance(solved_incident, dict):
        raise Exception("solved_example not a dict")

    pb_vars = {
        "src_file_name": file_name,
        "src_file_contents": file_contents,
        "analysis_line_number": str(line_number),
        "analysis_message": analysis_message,
    }

    print(solved_incident)

    if bool(solved_incident):
        solved_example = incident_store.select_accepted_solution(
            solved_incident["solution_id"]
        )
        pb_vars["solved_example_diff"] = solved_example["solution_small_diff"]
        pb_vars["solved_example_file_name"] = solved_incident["incident_uri"]

    pb = PromptBuilder(model_provider.get_prompt_builder_config(), pb_vars)
    prompt = pb.build_prompt()
    if isinstance(prompt, list):
        raise Exception(f"Did not supply proper variables. Need at least {prompt}")

    if stream:
        return model_provider.stream(prompt)
    else:
        return model_provider.invoke(prompt)


@routes.post("/get_incident_solution")
async def post_get_incident_solution(request: Request):
    """
    Will need to cache the incident result so that the user, when it accepts
    or rejects it knows what the heck the user is referencing

    Stateful, stores it

    params (json):
    - application_name (str)
    - ruleset_name (str)
    - violation_name (str)
    - incident_snip (str)
    - incident_variables (list)
    - file_name (str)
    - file_contents (str)
    - line_number: 0-indexed (let's keep it consistent)
    - analysis_message (str)

    return (json):
    - llm_output:
    """

    print(f"post_get_incident_solution recv'd: {request}")

    llm_output = get_incident_solution(await request.json(), False).content

    return web.json_response(
        {
            "llm_output": llm_output,
        }
    )


@routes.get("/ws/get_incident_solution")
async def ws_get_incident_solution(request: Request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    msg = await ws.receive()

    if msg.type == web.WSMsgType.TEXT:
        try:
            json_request = json.loads(msg.data)

            for chunk in get_incident_solution(json_request, True):
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


app = web.Application()
app.add_routes(routes)

incident_store: PSQLIncidentStore
model_provider: ModelProvider

if __name__ == "__main__":
    base_path = os.path.dirname(__file__)

    # TODO: Make this all config-based
    incident_store = PSQLIncidentStore(
        config_filepath=f"{base_path}/../kai/database.ini",
        config_section="postgresql",
        # emb_provider=EmbeddingInstructor(model="hkunlp/instructor-base"),
        emb_provider=EmbeddingNone(),
        drop_tables=False,
    )

    model_provider = IBMGraniteModel()
    # model_provider = IBMLlamaModel()
    # model_provider = OpenAIModel()

    web.run_app(app)


# NOTE: Dead code blocks. Keeping in tree for now just in case we decide to
# implement these functions

# def post_json(func: Callable[[dict], Any], schema_name: str):
#     async def wrapped_handler(request: Request):
#         schema: dict = json.loads(open(f"data/jsonschema/{schema_name}.json").read())
#         request_json: dict = await request.json()

#         try:
#             jsonschema.validate(instance=request_json, schema=schema)
#         except jsonschema.ValidationError as err:
#             raise web.HTTPUnprocessableEntity(text=f"{err}")

#         # TODO: Make better
#         try:
#             result = func(request_json)
#         except web.HTTPException
#         except Exception as err:
#             return web.HTTPException(text=f"{err}")

#         if isinstance(result, dict):
#             return web.json_response(result)
#         elif isinstance(result, list):
#             return web.json_response(result)
#         elif isinstance(result, str):
#             return web.Response(text=result)
#         else:
#             return web.Response(text=str(result))

#     return wrapped_handler

# def accept_or_reject_solution(params):
#     """
#     User says which solution and whether to reject or accept it

#     params (json):
#     - id: the id of the incident to accept or reject
#     - accept: bool to say yes or no

#     return (json):
#     - success: duh
#     """

#     id = params["id"]
#     accept = params["accept"]

#     if accept:
#         solution = get_solution_from_id(id)
#         put_solution_in_indicent_store(solution)

#     return json.dump({"success": True})