repos = {
    "eap-coolstore-monolith": [
        "https://github.com/mathianasj/eap-coolstore-monolith.git",
        "main",
        "quarkus-migration",
    ],
    "kitchensink": [
        "https://github.com/tqvarnst/jboss-eap-quickstarts.git",
        "main",
        "quarkus-3.2",
    ],
    ###
    # Commenting ticket-monster out until we know we want to add this in as an example
    # Analyzing ticket-monster is adding ~20-60 mins extra time on analysis runs and at
    # moment we are leaning towards using CoolStore instead of TicketMonster as an example
    ##
    # "ticket-monster": ["https://github.com/jmle/monolith.git", "master", "quarkus"],
    "helloworld-mdb": [
        "https://github.com/savitharaghunathan/helloworld-mdb.git",
        "main",
        "quarkus",
    ],
    "bmt": ["https://github.com/konveyor-ecosystem/bmt.git", "main", "quarkus"],
    "cmt": ["https://github.com/konveyor-ecosystem/cmt.git", "main", "quarkus"],
    "tasks-qute": [
        "https://github.com/konveyor-ecosystem/tasks-qute.git",
        "main",
        "quarkus",
    ],
    "greeter": ["https://github.com/konveyor-ecosystem/greeter.git", "main", "quarkus"],
    "ejb-remote": [
        "https://github.com/konveyor-ecosystem/ejb-remote.git",
        "main",
        "quarkus",
    ],
    "ejb-security": [
        "https://github.com/konveyor-ecosystem/ejb-security.git",
        "main",
        "quarkus",
    ],
}

sample_source_apps = {
    "eap-coolstore-monolith": "sample_repos/eap-coolstore-monolith",
    # "ticket-monster": "sample_repos/ticket-monster",
    "kitchensink": "sample_repos/kitchensink/kitchensink",
    "helloworld-mdb": "sample_repos/helloworld-mdb",
    "bmt": "sample_repos/bmt",
    "cmt": "sample_repos/cmt",
    "ejb-remote": "sample_repos/ejb-remote",
    "ejb-security": "sample_repos/ejb-security",
    "tasks-qute": "sample_repos/tasks-qute",
    "greeter": "sample_repos/greeter",
}

sample_target_apps = {
    "eap-coolstore-monolith": "sample_repos/eap-coolstore-monolith",
    # "ticket-monster": "sample_repos/ticket-monster",
    "kitchensink": "sample_repos/kitchensink/kitchensink",
    "helloworld-mdb": "sample_repos/helloworld-mdb",
    "bmt": "sample_repos/bmt",
    "cmt": "sample_repos/cmt",
    "ejb-remote": "sample_repos/ejb-remote",
    "ejb-security": "sample_repos/ejb-security",
    "tasks-qute": "sample_repos/tasks-qute",
    "greeter": "sample_repos/greeter",
}
