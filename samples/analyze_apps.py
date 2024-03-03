#!/usr/bin/env python

import os
import subprocess  # trunk-ignore(bandit)
import sys

from config import repos, sample_source_apps, sample_target_apps


# skip jboss-eap-quickstarts-quarkus
def analyze_apps():
    # perform analysis
    for repo in sample_source_apps:
        source_dir = sample_source_apps[repo]
        analyze(source_dir, repo, "initial")

    # switch to quarkus branch and perform analysis again
    # skip jboss-eap-quickstarts
    for repo in repos:
        if repo == "jboss-eap-quickstarts":
            continue
        print(f"Switching to {repos[repo][2]} branch for {repo}...")
        os.chdir(f"sample_repos/{repo}")
        if repos[repo][2] is not None:
            os.system(f"git checkout {repos[repo][2]}")  # trunk-ignore(bandit)
        os.chdir("../../")

    for repo in sample_target_apps:
        # perform analysis
        source_dir = sample_target_apps[repo]
        analyze(source_dir, repo, "solved")


def ensure_kantra_bin_exists():
    kantra_bin = os.path.join(os.getcwd(), "bin/kantra")
    print(f"Checking for Kantra binary at {kantra_bin}")
    if not os.path.isfile(kantra_bin):
        sys.exit(f"Unable to find {kantra_bin}\nPlease install Kantra")


def ensure_output_dir_exists(output_dir):
    if not os.path.isdir(output_dir):
        print(f"Creating output directory '{output_dir}'")
        # os.mkdir(output_dir)
        os.makedirs(output_dir)


def analyze(source_dir, name, target):
    ensure_kantra_bin_exists()
    full_output_dir = os.path.join(os.getcwd(), f"analysis_reports/{name}/{target}")
    ensure_output_dir_exists(full_output_dir)
    print(f"Analyzing '{source_dir}', will write output to '{full_output_dir}'")
    cmd = f'time ./bin/kantra analyze -i {source_dir} -m source-only -t "quarkus" -t "jakarta-ee" -t "jakarta-ee8+" -t "jakarta-ee9+" -t "cloud-readiness" --rules ./custom_rules -o {full_output_dir} --overwrite'
    subprocess.run(cmd, shell=True)  # trunk-ignore(bandit)


if __name__ == "__main__":
    analyze_apps()
