import argparse
import datetime
import enum
import os
from typing import Any, Optional
from urllib.parse import unquote, urlparse

from git import Repo
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    create_engine,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from sqlalchemy.types import JSON

from kai.kai_logging import KAI_LOG
from kai.models.kai_config import KaiConfig, KaiConfigIncidentStorePostgreSQLArgs
from kai.report import Report
from kai.service.incident_store.incident_store import (
    Application,
    IncidentStore,
    Solution,
    filter_incident_vars,
    load_reports_from_directory,
    remove_known_prefixes,
)

# have a logical category of un-mutated reports and one with the mutations


class Base(DeclarativeBase):
    type_annotation_map = {
        dict[str, Any]: JSON().with_variant(JSONB(), "postgresql"),
        list[str]: JSON().with_variant(JSONB(), "postgresql"),
    }


class ViolationCategory(enum.Enum):
    potential = "potential"
    optional = "optional"
    mandatory = "mandatory"


class PSQLApplication(Base):
    __tablename__ = "applications"

    application_name: Mapped[str] = mapped_column(primary_key=True)

    repo_uri_origin: Mapped[str]
    repo_uri_local: Mapped[str]
    current_branch: Mapped[str]
    current_commit: Mapped[str]
    generated_at: Mapped[datetime.datetime]

    incidents: Mapped[list["PSQLIncident"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class PSQLRuleset(Base):
    __tablename__ = "rulesets"

    ruleset_name: Mapped[str] = mapped_column(primary_key=True)

    tags: Mapped[list[str]]

    violations: Mapped[list["PSQLViolation"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )


class PSQLViolation(Base):
    __tablename__ = "violations"

    violation_name: Mapped[str] = mapped_column(primary_key=True)
    ruleset_name: Mapped[int] = mapped_column(
        ForeignKey("rulesets.ruleset_name"), primary_key=True
    )

    category: Mapped[ViolationCategory]
    labels: Mapped[list[str]]

    ruleset: Mapped[PSQLRuleset] = relationship(back_populates="violations")
    incidents: Mapped[list["PSQLIncident"]] = relationship(
        back_populates="violation", cascade="all, delete-orphan"
    )


class PSQLAcceptedSolution(Base):
    __tablename__ = "accepted_solutions"

    solution_id: Mapped[int] = mapped_column(primary_key=True)

    generated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(), server_default=func.now()
    )
    solution_big_diff: Mapped[str]
    solution_small_diff: Mapped[str]
    solution_original_code: Mapped[str]
    solution_updated_code: Mapped[str]

    incidents: Mapped[list["PSQLIncident"]] = relationship(
        back_populates="solution", cascade="all, delete-orphan"
    )


class PSQLIncident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[int] = mapped_column(primary_key=True)

    violation_name = Column(String)
    ruleset_name = Column(String)
    application_name: Mapped[str] = mapped_column(
        ForeignKey("applications.application_name")
    )
    incident_uri: Mapped[str]
    incident_snip: Mapped[str]
    incident_line: Mapped[int]
    incident_variables: Mapped[dict[str, Any]]
    solution_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("accepted_solutions.solution_id")
    )

    __table_args__ = (
        ForeignKeyConstraint(
            [violation_name, ruleset_name],
            [PSQLViolation.violation_name, PSQLViolation.ruleset_name],
        ),
        {},
    )

    violation: Mapped[PSQLViolation] = relationship(back_populates="incidents")
    application: Mapped[PSQLApplication] = relationship(back_populates="incidents")
    solution: Mapped[PSQLAcceptedSolution] = relationship(back_populates="incidents")


# def dump(sql, *multiparams, **params):
#     print(sql.compile(dialect=engine.dialect))

# engine = create_engine('postgresql://', strategy='mock', executor=dump)
# Base.metadata.create_all(engine, checkfirst=False)

# exit()


# TODO(@JonahSussman): Migrate this to use an ORM
class PSQLIncidentStore(IncidentStore):
    def __init__(self, args: KaiConfigIncidentStorePostgreSQLArgs):
        self.engine = create_engine(
            f"postgresql://{args.user}:{args.password}@{args.host}:5432/{args.database}"
        )

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def delete_store(self):
        Base.metadata.drop_all(self.engine)
        self.create_tables()

    def load_report(self, app: Application, report: Report) -> tuple[int, int, int]:
        """
        Returns: (number_new_incidents, number_unsolved_incidents,
        number_solved_incidents): tuple[int, int, int]
        """
        # FIXME: Only does stuff within the same application. Maybe fixed?

        # NEW: Store whole report in table
        # - if we get the same report again, we should skip adding it. Have some identifier
        # - But should still check incidents.

        # - have two tables `unsolved_incidents` and `solved_incidents`

        # Iterate through all incidents in the report
        # - change so theres an identified like "commit application ruleset violation"

        # create entries if not exists
        # reference the old-new matrix
        #           old
        #         | NO     | YES
        # --------|--------+-----------------------------
        # new NO  | -      | update (SOLVED, embeddings)
        #     YES | insert | update (line number, etc...)

        repo_path = unquote(urlparse(app.repo_uri_local).path)
        repo = Repo(repo_path)
        old_commit: str
        new_commit = app.current_commit

        number_new_incidents = 0
        number_unsolved_incidents = 0
        number_solved_incidents = 0

        with Session(self.engine) as session:
            incidents_temp: list[PSQLIncident] = []

            select_application_stmt = select(PSQLApplication).where(
                PSQLApplication.application_name == app.application_name
            )

            application = session.scalars(select_application_stmt).first()

            if application is None:
                application = PSQLApplication(
                    application_name=app.application_name,
                    repo_uri_origin=app.repo_uri_origin,
                    repo_uri_local=app.repo_uri_local,
                    current_branch=app.current_branch,
                    current_commit=app.current_commit,
                    generated_at=app.generated_at,
                )
                session.add(application)
                session.commit()

            old_commit = application.current_commit

            report_dict = dict(report)

            for ruleset_name, ruleset_dict in report_dict.items():
                select_ruleset_stmt = select(PSQLRuleset).where(
                    PSQLRuleset.ruleset_name == ruleset_name
                )

                ruleset = session.scalars(select_ruleset_stmt).first()

                if ruleset is None:
                    ruleset = PSQLRuleset(
                        ruleset_name=ruleset_name,
                        tags=ruleset_dict.get("tags", []),
                    )
                    session.add(ruleset)
                    session.commit()

                for violation_name, violation_dict in ruleset_dict.get(
                    "violations", {}
                ).items():
                    select_violation_stmt = (
                        select(PSQLViolation)
                        .where(PSQLViolation.violation_name == violation_name)
                        .where(PSQLViolation.ruleset_name == ruleset.ruleset_name)
                    )

                    violation = session.scalars(select_violation_stmt).first()

                    if violation is None:
                        violation = PSQLViolation(
                            violation_name=violation_name,
                            ruleset_name=ruleset.ruleset_name,
                            category=violation_dict.get("category", "potential"),
                            labels=violation_dict.get("labels", []),
                        )
                        session.add(violation)
                        session.commit()

                    for incident in violation_dict.get("incidents", []):
                        incidents_temp.append(
                            PSQLIncident(
                                violation_name=violation.violation_name,
                                ruleset_name=ruleset.ruleset_name,
                                application_name=application.application_name,
                                incident_uri=incident.get("uri", ""),
                                incident_snip=incident.get("codeSnip", ""),
                                incident_line=incident.get("lineNumber", 0),
                                incident_variables=incident.get("variables", {}),
                            )
                        )

            new_incidents = set(incidents_temp) - set(application.incidents)
            number_new_incidents = len(new_incidents)

            for new_incident in new_incidents:
                session.add(new_incident)

            session.commit()

            unsolved_incidents = set(application.incidents).intersection(incidents_temp)
            number_unsolved_incidents = len(unsolved_incidents)

            # incidents - incidents_temp
            solved_incidents = set(application.incidents) - set(incidents_temp)
            number_solved_incidents = len(solved_incidents)
            KAI_LOG.debug(f"Number of solved incidents: {len(solved_incidents)}")

            for solved_incident in solved_incidents:
                file_path = os.path.join(
                    repo_path,
                    # NOTE: When retrieving uris from the report, some of them
                    # had "/tmp/source-code/" as their root path. Unsure where
                    # it originates from.
                    unquote(urlparse(solved_incident.incident_uri).path).removeprefix(
                        "/tmp/source-code/"  # trunk-ignore(bandit/B108)
                    ),
                )
                big_diff = repo.git.diff(old_commit, new_commit)

                try:
                    original_code = repo.git.show(f"{old_commit}:{file_path}")
                except Exception as e:
                    KAI_LOG.error(e)
                    original_code = ""

                try:
                    updated_code = repo.git.show(f"{new_commit}:{file_path}")
                except Exception as e:
                    KAI_LOG.error(e)
                    updated_code = ""

                # file_path = pathlib.Path(os.path.join(repo_path, unquote(urlparse(si[3]).path).removeprefix('/tmp/source-code'))).as_uri()
                small_diff = repo.git.diff(old_commit, new_commit, "--", file_path)
                KAI_LOG.debug(small_diff)

                solved_incident.solution = PSQLAcceptedSolution(
                    generated_at=app.generated_at,
                    solution_big_diff=big_diff,
                    solution_small_diff=small_diff,
                    solution_original_code=original_code,
                    solution_updated_code=updated_code,
                )

            application.repo_uri_origin = app.repo_uri_origin
            application.repo_uri_local = app.repo_uri_local
            application.current_branch = app.current_branch
            application.current_commit = app.current_commit
            application.generated_at = app.generated_at

            session.commit()

        return number_new_incidents, number_unsolved_incidents, number_solved_incidents

    def find_solutions(
        self,
        ruleset_name: str,
        violation_name: str,
        incident_variables: dict,
        incident_snip: str | None = None,
    ) -> list[Solution]:
        if incident_snip is None:
            incident_snip = ""

        with Session(self.engine) as session:
            select_violation_stmt = (
                select(PSQLViolation)
                .where(PSQLViolation.violation_name == violation_name)
                .where(PSQLViolation.ruleset_name == ruleset_name)
            )

            violation = session.scalars(select_violation_stmt).first()

            if violation is None:
                return []

            select_incidents_with_solutions_stmt = (
                select(PSQLIncident)
                .where(PSQLIncident.violation_name == violation.violation_name)
                .where(PSQLIncident.ruleset_name == violation.ruleset_name)
                .where(PSQLIncident.solution_id.isnot(None))
                .where(PSQLIncident.incident_variables.op("<@")(incident_variables))
                .where(PSQLIncident.incident_variables.op("@>")(incident_variables))
            )

            result: list[Solution] = []
            for incident in session.execute(select_incidents_with_solutions_stmt):
                select_accepted_solution_stmt = select(PSQLAcceptedSolution).where(
                    PSQLAcceptedSolution.solution_id == incident.solution_id
                )

                accepted_solution = session.scalars(
                    select_accepted_solution_stmt
                ).first()

                result.append(
                    Solution(
                        uri=incident.incident_uri,
                        file_diff=accepted_solution.solution_small_diff,
                        repo_diff=accepted_solution.solution_big_diff,
                    )
                )

            return result


def main():
    KAI_LOG.setLevel("debug".upper())

    parser = argparse.ArgumentParser(description="Process some parameters.")
    parser.add_argument(
        "--config_filepath",
        type=str,
        default="../../config.toml",
        help="Path to the config file.",
    )
    parser.add_argument(
        "--drop_tables", type=str, default="False", help="Whether to drop tables."
    )
    parser.add_argument(
        "--analysis_dir_path",
        type=str,
        default="../../samples/analysis_reports",
        help="Path to analysis reports folder",
    )

    args = parser.parse_args()

    config = KaiConfig.model_validate_filepath(args.config_filepath)

    if config.incident_store.provider != "postgresql":
        raise Exception("This script only works with PostgreSQL incident store.")

    incident_store = PSQLIncidentStore(config.incident_store.args)

    if args.drop_tables:
        incident_store.delete_store()

    load_reports_from_directory(incident_store, args.analysis_dir_path)


if __name__ == "__main__":
    main()
