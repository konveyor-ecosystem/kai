import os
import string
from dataclasses import dataclass, field
from os import path

import yaml

from kai.kai_logging import KAI_LOG

T_DIR = path.join(path.dirname(__file__), "data/templates")


# TODO: Variants
class Section:
    """
    Simple data class containing the template and the variables for a section
    """

    @staticmethod
    def from_dict(x: dict):
        return Section(
            uuid=x.get("uuid", None),
            file_path=x.get("file_path", None),
            template=x.get("template", None),
            default_vars=x.get("default_vars", None),
            build_steps=x.get("build_steps", None),
        )

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "file_path": self.file_path,
            "template": self.template,
            "default_vars": self.default_vars,
            "build_steps": self.build_steps,
        }

    def __init__(
        self,
        *,
        uuid: str = None,
        file_path: str = None,
        template: str = None,
        default_vars: dict[str, str] = None,
        build_steps: list = None,
    ):
        if uuid is None:
            raise Exception("uuid can't be none")
        self.uuid = uuid

        if file_path is not None and template is not None:
            raise Exception("Can't provide both file_path and template")
        elif file_path is not None:
            self.file_path = path.join(T_DIR, file_path)
            self.template = open(self.file_path).read()
        elif template is not None:
            self.file_path = "/dev/null"
            self.template = template
        else:
            self.file_path = "/dev/null"
            self.template = ""

        # NOTE: Should this go in pb_build instead?
        if build_steps is None:
            build_steps = [{"format": self.uuid}]

        self.build_steps = build_steps

        itr = string.Formatter().parse(self.template)
        self.vars = [v[1] for v in itr if v[1] is not None]
        self.default_vars = {} if default_vars is None else default_vars

    def __hash__(self):
        return hash((self.file_path, self.template))

    def is_valid(self, vars_dict: dict[str, str]):
        vars_dict = self.default_vars | vars_dict

        for v in self.vars:
            if v not in vars_dict:
                return False

        return True

    def format(self, vars_dict: dict[str, str]):
        vars_dict = self.default_vars | vars_dict

        return self.template.format(**vars_dict)

    def format_with_raise(self, vars_dict: dict[str, str]):
        if self.is_valid(vars_dict):
            return self.format(vars_dict)

        raise PBError(
            f"Missing variables: {set(self.vars).difference(set(vars_dict))} for section '{self.uuid}'"
        )


class PBError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


@dataclass
class Symbol:
    value: str

    def __hash__(self):
        return hash(self.value)


@dataclass
class Env:
    inner: dict = field(default_factory=dict)
    outer: "Env" = None

    def find(self, x: str):
        if x in self.inner:
            return self.inner

        if self.outer is not None:
            return self.outer.find(x)

        return None


def pb_concat(args: list, pb_env: Env, pb_vars: dict) -> str:
    """
    Description:
        concat: [ arg... ] -> result

        Takes a list of arguments, evaluates them and concatenates the results.
        Returns the concatenation. If the arguments are not strings, throws an
        error.

    Arguments:
        arg (str optional) - The string to concat

    Returns:
        result (str) - The concatenated string

    Errors:
        If any error is encountered, throws a PBError
    """
    result = ""

    for arg in args:
        arg = pb_eval(arg, pb_env, pb_vars)
        if not isinstance(arg, str):
            raise PBError(f"Can only concat strings. Got {type(arg)}.")
        result += arg

    return result


def pb_format(args: list, pb_env: Env, pb_vars: dict) -> str:
    """
    Description:
        format: symbol pb_var_key -> result

        Takes the section specified by symbol and formats it using Python's
        .format and pb_vars as the argument. If pb_var_key is specified, then it
        looks up that value in pb_vars, and uses that dict instead. If the value
        for pb_var_key is list[dict] instead, format will run multiple times for
        each entry in the list and concatenate the results.

    Arguments:
        symbol (str optional) - The string to look up in pb_vars
        pb_var_key (str optional) - The key in pb_vars to use, if wanted

    Returns:
        result (str) - The formatted string

    Errors:
        If any error is encountered, throws a PBError
    """

    KAI_LOG.debug(f"pb_format: {args=}")
    if len(args) > 2:
        raise PBError(f"pb_format: Max 2 arguments. Got {len(args)}")
    if len(args) == 0:
        return ""

    section = pb_eval(args[0], pb_env, pb_vars)
    if not isinstance(section, Section):
        raise PBError(f"pb_format: First argument not a Section. Got {type(section)}")

    if len(args) == 1:
        return section.format_with_raise(pb_vars)

    pb_vars_key = pb_eval(args[1], pb_env, pb_vars)
    try:
        pb_vars = pb_vars[pb_vars_key]
    except KeyError as e:
        raise PBError(f"pb_build: Could not find key in pb_vars: {pb_vars_key}") from e

    # pb_vars = pb_vars[pb_eval(args[1], pb_env, pb_vars)]
    if isinstance(pb_vars, dict):
        return section.format_with_raise(pb_vars)
    if not isinstance(pb_vars, list):
        raise PBError(
            f"pb_format: If using with pb_var_key, pb_vars[pb_var_key] must be a list. Got {type(pb_vars)}"
        )
    for x in pb_vars:
        if not isinstance(x, dict):
            raise PBError(
                f"pb_format: If using with pb_var_key, pb_vars[pb_var_key] each element must be a list. Got {type(x)}"
            )

    result = ""
    for vars in pb_vars:
        s = section.format_with_raise(vars)
        result += s

    return result


def pb_build(args: list, pb_env: Env, pb_vars: dict):
    """
    Description:
        build: symbol pb_var_key -> result

        Takes the section specified by symbol and builds it using the section's
        build_steps. (Note: Section has a build step of simply formatting the
        string). If pb_var_key is specified, then it looks up that value in
        pb_vars, and uses that dict instead. If the value for pb_var_key is
        list[dict] instead, format will run multiple times for each entry in the
        list and concatenate the results.

    Arguments:
        symbol (str optional) - The string to look up in pb_vars pb_var_key (str
        optional) - The key in pb_vars to use, if wanted

    Returns:
        result (str) - The formatted string

    Errors:
        If any error is encountered, throws a PBError
    """

    # print(f"pb_format: {args=}")
    if len(args) > 2:
        raise PBError(f"pb_build: Max 2 arguments. Got {len(args)}")
    if len(args) == 0:
        return ""

    section = pb_eval(args[0], pb_env, pb_vars)
    if not isinstance(section, Section):
        raise PBError(f"pb_build: First argument not a Section. Got {type(section)}")

    if len(args) == 1:
        for s in section.build_steps:
            result = pb_eval(s, pb_env, pb_vars)
        return result

    pb_vars_key = pb_eval(args[1], pb_env, pb_vars)
    try:
        pb_vars = pb_vars[pb_vars_key]
    except KeyError as e:
        raise PBError(f"pb_build: Could not find key in pb_vars: {pb_vars_key}") from e

    # pb_vars = pb_vars[pb_eval(args[1], pb_env, pb_vars)]
    if isinstance(pb_vars, dict):
        for s in section.build_steps:
            r = pb_eval(s, pb_env, pb_vars)
        return r
    if not isinstance(pb_vars, list):
        raise PBError(
            f"pb_build: If using with pb_var_key, pb_vars[pb_var_key] must be a list. Got {type(pb_vars)}"
        )
    for x in pb_vars:
        if not isinstance(x, dict):
            raise PBError(
                f"pb_build: If using with pb_var_key, pb_vars[pb_var_key] each element must be a list. Got {type(x)}"
            )

    result = ""
    for vars in pb_vars:
        for s in section.build_steps:
            r = pb_eval(s, pb_env, vars)
        result += r

    return result


def pb_one_of(args: list, pb_env: Env, pb_vars: dict) -> str:
    """
    Description:
        one_of: [ arg... ] -> result

        Goes through each argument sequentially and returns the argument that
        does not error. Raises an error if the argument is not a string (for
        now). Returns the first argument that doesn't have an error.

    Arguments:
        arg (str) - Each argument to evaluate

    Returns:
        result (str) - The first argument that didn't error or returned a string
        when evaluated

    Errors:
        If any error is encountered, throws a PBError
    """

    errors = []
    for arg in args:
        try:
            arg = pb_eval(arg, pb_env, pb_vars)
            # NOTE: Maybe we could expand this to more than just strings
            if not (isinstance(arg, str) or arg is None):
                raise PBError(f"one_of: Only supports str or None. Got {type(arg)}.")
            if arg is not None:
                return arg
        except Exception as e:
            errors.append(e)

    if len(errors) == 0:
        raise PBError(
            "one_of: None of the arguments had an error, but also didn't succeed?"
        )

    msg = "one_of: All of the arguments were invalid. Got the following errors:\n"
    for e in errors:
        msg += f"- {str(e)}\n"

    raise PBError(msg)


def pb_eval(x, pb_env: Env, pb_vars: dict):
    # print(f"pb_eval: {x}")
    if isinstance(x, Symbol) or (isinstance(x, str) and len(x) > 0 and x[0] == "$"):
        f = pb_env.find(x)
        if f is not None:
            return f[x]

        raise PBError(f"pb_eval: Couldn't find symbol {x}.")

    if not isinstance(x, dict):
        return x

    if len(list(x.keys())) != 1:
        raise PBError("Only one action at a time!")

    fn_name = list(x.keys())[0]
    if not isinstance(fn_name, str):
        raise PBError("Action key must be string!")

    fn_args = x[fn_name]
    if not isinstance(fn_args, list):
        fn_args = [fn_args]

    if fn_name == "quote" or fn_name == "q":
        return fn_args[0]

    func = pb_eval(Symbol(fn_name), pb_env, pb_vars)
    return func(fn_args, pb_env, pb_vars)


def standard_env():
    env = Env(
        inner={
            Symbol("concat"): pb_concat,
            Symbol("format"): pb_format,
            Symbol("build"): pb_build,
            Symbol("one_of"): pb_one_of,
        }
    )

    for dirpath, _dirnames, filenames in os.walk(T_DIR):
        for filename in filenames:
            if filename.endswith(".yaml"):
                file_path = os.path.join(dirpath, filename)
                x = open(file_path).read()

                documents = yaml.safe_load_all(x)

                for doc in documents:
                    section = Section.from_dict(doc)
                    if env.find(section.uuid) is not None:
                        raise Exception(f"{section.uuid} already exists!")
                    else:
                        env.inner[section.uuid] = section

    return env


global_env = standard_env()


CONFIG_IBM_GRANITE_MF = "$mf_ibm_model"
CONFIG_IBM_GRANITE = "$ibm_granite_model"
CONFIG_IBM_LLAMA = "$ibm_llama_model"


def build_prompt(section_name: str, pb_vars: dict):
    env = global_env.find(section_name)
    if env is None:
        raise PBError(f"Couldn't find section name: {section_name}")

    section = env[section_name]
    if not isinstance(section, Section):
        raise PBError(f"Not a section. Got type: {type(section)}")

    for step in section.build_steps:
        result = pb_eval(step, global_env, pb_vars)

    if not isinstance(result, str):
        raise PBError(f"Prompt building did not return str. Got type: {type(result)}")
    return result


if __name__ == "__main__":

    pb_vars = {
        "src_file_name": "/var/src_file_name.java",
        "src_file_contents": "import nothing;",
        "analysis_line_number": 10,
        "analysis_message": "ya done goofed!",
    }

    print(build_prompt(CONFIG_IBM_GRANITE, pb_vars))

    pb_vars = {
        "src_file_name": "/var/src_file_name.java",
        "solved_example_diff": "Here's a diff for ya!",
        "solved_example_file_name": "the/solved/example.java",
        "src_file_contents": "import nothing;",
        "analysis_line_number": 10,
        "analysis_message": "ya done goofed!",
    }

    print(build_prompt(CONFIG_IBM_GRANITE, pb_vars))

    pb_vars = {
        "src_file_name": "/var/src_file_name.java",
        "solved_example_before": "File before!",
        "solved_example_after": "File after!",
        "solved_example_file_name": "the/solved/example.java",
        "src_file_contents": "import nothing;",
        "analysis_line_number": 10,
        "analysis_message": "ya done goofed!",
    }

    print(build_prompt(CONFIG_IBM_GRANITE, pb_vars))

    # FIXME: Make pb_vars an environment, not a dict (cascading stuff)

    pb_vars = {
        "src_file_name": "/var/src_file_name.java",
        "src_file_language": "java",
        "src_file_contents": "import nothing;",
        "solved_example_file_name": "the/solved/example.java",
        "incidents": [
            {
                "issue_number": 1,
                "analysis_line_number": 10,
                "analysis_message": "ya done goofed!",
                "solved_example_before": "File before!",
                "solved_example_after": "File after!",
                "src_file_language": "java",
            }
        ],
    }

    print(build_prompt(CONFIG_IBM_GRANITE_MF, pb_vars))

    pb_vars = {
        "analysis_message": "test message",
        "src_file_name": "/var/src_file_name.java",
        "src_file_language": "java",
        "src_file_contents": "import nothing;",
        "analysis_line_number": 10,
    }

    print(build_prompt(CONFIG_IBM_LLAMA, pb_vars))
