import datetime
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import yaml
from git import Repo

from kai.constants import PATH_LOCAL_REPO
from kai.kai_logging import KAI_LOG
from kai.models.kai_config import KaiConfigIncidentStore, KaiConfigIncidentStoreProvider
from kai.report import Report

# These prefixes are sometimes in front of the paths, strip them.
# Also strip leading slashes since os.path.join can't join two absolute paths
KNOWN_PREFIXES = (
    # trunk-ignore(bandit/B108)
    "/tmp/source-code/",
    "/addon/source/",
    "/",
)


# These are known unique variables that can be included by incidents
# They would prevent matches that we actually want, so we filter them
# before adding to the database or searching
FILTERED_INCIDENT_VARS = ("file", "package")


def remove_known_prefixes(path: str) -> str:
    for prefix in KNOWN_PREFIXES:
        if path.startswith(prefix):
            return path.removeprefix(prefix)
    return path


def filter_incident_vars(incident_vars: dict):
    for v in FILTERED_INCIDENT_VARS:
        incident_vars.pop(v, None)
    return incident_vars


def __get_repo_path(app_name):
    """
    Get the repo path
    """
    return os.path.join(PATH_LOCAL_REPO, app_name)


def __get_app_variables(path: str, app_name: str):
    if not os.path.exists(path):
        KAI_LOG.error(
            f"Error: {app_name} does not exist in the analysis_reports directory."
        )
        return None

    # Path to the app.yaml file
    app_yaml_path = os.path.join(path, app_name, "app.yaml")
    # Check if app.yaml exists for the specified app
    if not os.path.exists(app_yaml_path):
        KAI_LOG.error(f"Error: app.yaml does not exist for {app_name}.")
        return None

    # Load contents of app.yaml
    with open(app_yaml_path, "r") as app_yaml_file:
        app_data: dict = yaml.safe_load(app_yaml_file)

    return app_data


# NOTE: Once we integrate with Konveyor, this most likely will not be necessary
def load_reports_from_directory(store: "IncidentStore", path: str):
    basedir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.dirname(basedir)
    folder_path = os.path.join(parent_dir, path)

    if not os.path.exists(folder_path):
        KAI_LOG.error(f"Error: {folder_path} does not exist.")
        return None
    if not os.listdir(folder_path):
        KAI_LOG.error(f"Error: {folder_path} is empty.")
        return None

    apps = os.listdir(folder_path)
    KAI_LOG.info(f"Loading incident store with applications: {apps}\n")

    for app in apps:
        # if app is a directory then check if there is a folder called initial
        KAI_LOG.info(f"Loading application {app}\n")
        app_path = os.path.join(folder_path, app)

        if not os.path.isdir(app_path):
            continue

        initial_folder = os.path.join(app_path, "initial")
        if not os.path.exists(initial_folder):
            KAI_LOG.error(f"Error: {initial_folder} does not exist.")
            return None

        # Check if the `initial` folder is empty
        if not os.listdir(initial_folder):
            KAI_LOG.error(f"Error: No analysis report found in {initial_folder}.")
            return None

        report_path = os.path.join(initial_folder, "output.yaml")

        repo_path = __get_repo_path(app)
        repo = Repo(repo_path)
        app_v = __get_app_variables(folder_path, app)
        initial_branch = app_v["initial_branch"]
        repo.git.checkout(initial_branch)
        commit = repo.head.commit

        app_initial = Application(
            application_name=app,
            repo_uri_origin=repo.remotes.origin.url,
            repo_uri_local=repo_path,
            current_branch=initial_branch,
            current_commit=commit.hexsha,
            generated_at=datetime.datetime.now(),
        )

        store.load_report(app_initial, Report.load_report_from_file(report_path))
        KAI_LOG.info(f"Loaded application - initial {app}\n")

        solved_folder = os.path.join(app_path, "solved")

        if not os.path.exists(solved_folder):
            KAI_LOG.error(f"Error: {solved_folder} does not exist.")
            return None

        if not os.listdir(solved_folder):
            KAI_LOG.error(f"Error: No analysis report found in {solved_folder}.")
            return None

        report_path = os.path.join(solved_folder, "output.yaml")
        solved_branch = __get_app_variables(folder_path, app)["solved_branch"]

        repo.git.checkout(solved_branch)
        commit = repo.head.commit
        app_solved = Application(
            application_name=app,
            repo_uri_origin=repo.remotes.origin.url,
            repo_uri_local=repo_path,
            current_branch=solved_branch,
            current_commit=commit.hexsha,
            generated_at=datetime.datetime.now(),
        )
        store.load_report(app_solved, Report.load_report_from_file(report_path))

        KAI_LOG.info(f"Loaded application - solved {app}\n")


@dataclass
class Application:
    application_name: str
    repo_uri_origin: str
    repo_uri_local: str
    current_branch: str
    current_commit: str
    generated_at: datetime.datetime


# NOTE(@JonahSussman): Should we include the incident that this solution is for
# inside the class?
@dataclass
class Solution:
    uri: str
    file_diff: str
    repo_diff: str
    original_code: Optional[str] = None
    updated_code: Optional[str] = None


class IncidentStore(ABC):

    @staticmethod
    def from_config(config: KaiConfigIncidentStore):
        """
        Factory method to produce whichever incident store is needed.
        """

        if config.provider == "postgresql":
            from kai.service.incident_store.psql import PSQLIncidentStore

            return PSQLIncidentStore(config.args)
        elif config.provider == "in_memory":
            from kai.service.incident_store.in_memory import InMemoryIncidentStore

            return InMemoryIncidentStore(config.args)
        else:
            raise ValueError(
                f"Unsupported provider: {config.provider}\ntype: {type(config.provider)}\nlmao: {KaiConfigIncidentStoreProvider.POSTGRESQL}"
            )

    @abstractmethod
    def load_report(
        self, application: Application, report: Report
    ) -> tuple[int, int, int]:
        """
        Load incidents from a report and given application object. Returns a
        tuple containing (# of new incidents, # of unsolved incidents, # of
        solved incidents) in that order.

        NOTE: This application object is more like metadata than anything.
        """
        pass

    @abstractmethod
    def delete_store(self):
        """
        Clears all data within the incident store. Non-reversible!
        """
        pass

    @abstractmethod
    def find_solutions(
        self,
        ruleset_name: str,
        violation_name: str,
        incident_variables: dict,
        incident_snip: Optional[str] = None,
    ) -> list[Solution]:
        """
        Returns a list of solutions for the given incident. Exact matches only.
        """
        pass
