const vscode = require("vscode");
const cp = require("child_process");
const path = require("path");


// =====================================================
// ARC STATION CONFIGURATION
// =====================================================

const CONTROLLER = process.env.ARC_STATION_CONTROLLER ||
    path.join(__dirname, "..", "controller.py");


// =====================================================
// ACTIVATE
// =====================================================

function activate(context) {

    console.log("");
    console.log("================================");
    console.log("ARC STATION EXTENSION STARTED");
    console.log("================================");


    // -------------------------------------------------
    // Send developer status
    // -------------------------------------------------

    function sendDeveloperStatus() {

        const folders =
            vscode.workspace.workspaceFolders;


        // ---------------------------------------------
        // No workspace yet
        // ---------------------------------------------

        if (
            !folders ||
            folders.length === 0
        ) {

            console.log(
                "ARC STATION: Waiting for project..."
            );

            return;
        }


        // ---------------------------------------------
        // Current project
        // ---------------------------------------------

        const project =
            folders[0];


        const projectName =
            project.name;


        const projectPath =
            project.uri.fsPath;


        console.log("");
        console.log(
            "ARC STATION PROJECT:"
        );

        console.log(
            projectName
        );

        console.log(
            "PATH:",
            projectPath
        );


        // ---------------------------------------------
        // Get Git status
        // ---------------------------------------------

        getGitStatus(
            projectPath,
            function (gitData) {


                const command =
                    [
                        "DEV",
                        projectName,
                        gitData.git,
                        gitData.branch,
                        gitData.changes,
                        gitData.commits
                    ].join("|");


                console.log(
                    "ARC STATION COMMAND:"
                );

                console.log(
                    command
                );


                // -------------------------------------
                // Send to controller
                // -------------------------------------

                sendToController(
                    command
                );

            }
        );
    }


    // =================================================
    // GIT STATUS
    // =================================================

    function getGitStatus(
        projectPath,
        callback
    ) {


        // ---------------------------------------------
        // Check Git repository
        // ---------------------------------------------

        cp.execFile(

            "git",

            [
                "-C",
                projectPath,
                "rev-parse",
                "--is-inside-work-tree"
            ],

            function (
                error,
                stdout
            ) {


                if (
                    error ||
                    stdout.trim() !== "true"
                ) {

                    callback({

                        git: "NO GIT",

                        branch: "--",

                        changes: "0",

                        commits: "0"

                    });

                    return;
                }


                // -------------------------------------
                // Branch
                // -------------------------------------

                cp.execFile(

                    "git",

                    [
                        "-C",
                        projectPath,
                        "branch",
                        "--show-current"
                    ],

                    function (
                        branchError,
                        branchStdout
                    ) {


                        const branch =
                            branchError
                                ? "--"
                                : (
                                    branchStdout.trim()
                                    || "DETACHED"
                                );


                        // ---------------------------------
                        // Changes
                        // ---------------------------------

                        cp.execFile(

                            "git",

                            [
                                "-C",
                                projectPath,
                                "status",
                                "--porcelain"
                            ],

                            function (
                                statusError,
                                statusStdout
                            ) {


                                const lines =
                                    statusError
                                        ? []
                                        : statusStdout
                                            .trim()
                                            .split("\n")
                                            .filter(Boolean);


                                const changes =
                                    lines.length;


                                const git =
                                    changes === 0
                                        ? "CLEAN"
                                        : "CHANGES";


                                // ---------------------------------
                                // Commits
                                // ---------------------------------

                                cp.execFile(

                                    "git",

                                    [
                                        "-C",
                                        projectPath,
                                        "rev-list",
                                        "--count",
                                        "HEAD"
                                    ],

                                    function (
                                        commitError,
                                        commitStdout
                                    ) {


                                        const commits =
                                            commitError
                                                ? "0"
                                                : (
                                                    commitStdout.trim()
                                                    || "0"
                                                );


                                        callback({

                                            git: git,

                                            branch: branch,

                                            changes:
                                                String(
                                                    changes
                                                ),

                                            commits:
                                                commits

                                        });

                                    }
                                );

                            }
                        );

                    }
                );

            }
        );
    }


    // =================================================
    // SEND TO PYTHON CONTROLLER
    // =================================================

    function sendToController(
        command
    ) {

        console.log(
            "ARC STATION: Sending to controller..."
        );


        cp.execFile(

            "python3",

            [
                CONTROLLER,
                command
            ],

            function (
                error,
                stdout,
                stderr
            ) {


                if (error) {

                    console.error(
                        "ARC STATION CONTROLLER ERROR:"
                    );

                    console.error(
                        error.message
                    );

                    return;
                }


                if (stdout) {

                    console.log(
                        "CONTROLLER:"
                    );

                    console.log(
                        stdout
                    );
                }


                if (stderr) {

                    console.error(
                        "CONTROLLER STDERR:"
                    );

                    console.error(
                        stderr
                    );
                }

            }
        );
    }


    // =================================================
    // START TRACKING
    // =================================================

    function startTracking() {

        console.log(
            "ARC STATION: Starting project tracking..."
        );


        // ---------------------------------------------
        // Try immediately
        // ---------------------------------------------

        sendDeveloperStatus();


        // ---------------------------------------------
        // Try again after VS Code has finished loading
        // ---------------------------------------------

        setTimeout(
            function () {

                console.log(
                    "ARC STATION: Initial delayed update"
                );

                sendDeveloperStatus();

            },
            1500
        );


        // ---------------------------------------------
        // Try again after 3 seconds
        // ---------------------------------------------

        setTimeout(
            function () {

                console.log(
                    "ARC STATION: Second delayed update"
                );

                sendDeveloperStatus();

            },
            3000
        );

    }


    // =================================================
    // PROJECT / WORKSPACE CHANGE
    // =================================================

    const workspaceListener =
        vscode.workspace.onDidChangeWorkspaceFolders(

            function () {

                console.log(
                    "ARC STATION: Workspace changed"
                );

                setTimeout(
                    sendDeveloperStatus,
                    500
                );

            }

        );


    context.subscriptions.push(
        workspaceListener
    );


    // =================================================
    // FILE SAVE
    // =================================================

    const fileListener =
        vscode.workspace.onDidSaveTextDocument(

            function () {

                console.log(
                    "ARC STATION: File saved"
                );

                sendDeveloperStatus();

            }

        );


    context.subscriptions.push(
        fileListener
    );


    // =================================================
    // PERIODIC GIT CHECK
    // =================================================

    const timer =
        setInterval(

            function () {

                sendDeveloperStatus();

            },

            5000

        );


    context.subscriptions.push({

        dispose: function () {

            clearInterval(
                timer
            );

        }

    });


    // =================================================
    // START
    // =================================================

    startTracking();


    console.log(
        "ARC STATION: Git tracking active"
    );

}


// =====================================================
// DEACTIVATE
// =====================================================

function deactivate() {

    console.log(
        "ARC STATION EXTENSION STOPPED"
    );

}


// =====================================================
// EXPORT
// =====================================================

module.exports = {

    activate,

    deactivate

};