import subprocess
import time
import os


# =====================================================
# ARC STATION AUTOMATIC PROJECT TRACKER
# =====================================================

CONTROLLER = os.path.expanduser(
    "~/Documents/04-Program/ArcStation/controller.py"
)

CHECK_INTERVAL = 2

last_command = ""
last_project = None

# Cache discovered project paths
project_cache = {}


# =====================================================
# GET FRONT VS CODE WINDOW TITLE
# =====================================================

def get_vscode_window_title():

    script = '''
    tell application "System Events"

        if not (exists process "Code") then
            return ""
        end if

        tell process "Code"

            if (count of windows) = 0 then
                return ""
            end if

            return name of front window

        end tell

    end tell
    '''

    try:

        result = subprocess.run(
            [
                "osascript",
                "-e",
                script
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        title = result.stdout.strip()

        if not title:
            return None

        return title

    except Exception as error:

        print(
            "Window detection error:",
            error
        )

        return None


# =====================================================
# GET PROJECT NAME FROM VS CODE TITLE
# =====================================================

def clean_project_name(title):

    if not title:
        return None

    title = title.strip()

    # -------------------------------------------------
    # Examples:
    #
    # git_tracker.py — Website Dev
    # App.js — DrinkItUp
    # main.cpp — AlgoTrack
    #
    # We want:
    #
    # Website Dev
    # DrinkItUp
    # AlgoTrack
    # -------------------------------------------------

    if " — " in title:

        project_name = title.rsplit(
            " — ",
            1
        )[1].strip()

    elif " - " in title:

        project_name = title.rsplit(
            " - ",
            1
        )[1].strip()

    else:

        project_name = title


    # -------------------------------------------------
    # Remove VS Code suffix
    # -------------------------------------------------

    project_name = project_name.replace(
        "Visual Studio Code",
        ""
    ).strip()


    if not project_name:

        return None


    return project_name


# =====================================================
# FIND PROJECT FOLDER
# =====================================================

def find_project_folder(project_name):

    # -------------------------------------------------
    # CHECK CACHE FIRST
    # -------------------------------------------------

    if project_name in project_cache:

        cached_path = project_cache[
            project_name
        ]

        if os.path.isdir(
            cached_path
        ):

            return cached_path


    # -------------------------------------------------
    # SEARCH ROOTS
    # -------------------------------------------------

    search_roots = [

        os.path.expanduser(
            "~/Documents"
        ),

        os.path.expanduser(
            "~/Desktop"
        )
    ]


    # -------------------------------------------------
    # SEARCH
    # -------------------------------------------------

    for root in search_roots:

        if not os.path.isdir(
            root
        ):

            continue


        try:

            result = subprocess.run(
                [
                    "find",

                    root,

                    "-type",
                    "d",

                    "-name",
                    project_name,

                    "-not",
                    "-path",
                    "*/node_modules/*",

                    "-not",
                    "-path",
                    "*/.git/*",

                    "-not",
                    "-path",
                    "*/Library/*",

                    "-not",
                    "-path",
                    "*/dist/*",

                    "-not",
                    "-path",
                    "*/build/*"
                ],

                capture_output=True,

                text=True,

                timeout=10
            )


            paths = [

                path.strip()

                for path
                in result.stdout.splitlines()

                if path.strip()

            ]


            # -------------------------------------------------
            # PREFER GIT PROJECT
            # -------------------------------------------------

            for path in paths:

                git_path = os.path.join(
                    path,
                    ".git"
                )


                if os.path.exists(
                    git_path
                ):

                    project_cache[
                        project_name
                    ] = path

                    return path


            # -------------------------------------------------
            # NON-GIT PROJECT
            # -------------------------------------------------

            if paths:

                project_cache[
                    project_name
                ] = paths[0]

                return paths[0]


        except Exception as error:

            print(
                "Project search error:",
                error
            )


    return None


# =====================================================
# RUN GIT COMMAND
# =====================================================

def git_command(
    project,
    arguments
):

    try:

        result = subprocess.run(
            [
                "git",

                "-C",

                project,

                *arguments
            ],

            capture_output=True,

            text=True,

            timeout=5
        )


        if result.returncode != 0:

            return None


        return result.stdout.strip()


    except Exception:

        return None


# =====================================================
# GET GIT STATUS
# =====================================================

def get_git_status(
    project
):

    # -------------------------------------------------
    # CHECK GIT REPOSITORY
    # -------------------------------------------------

    repository = git_command(
        project,

        [
            "rev-parse",

            "--is-inside-work-tree"
        ]
    )


    if repository != "true":

        return {

            "git": "NO GIT",

            "branch": "--",

            "changes": "0",

            "commits": "0"
        }


    # -------------------------------------------------
    # BRANCH
    # -------------------------------------------------

    branch = git_command(
        project,

        [
            "branch",

            "--show-current"
        ]
    )


    if not branch:

        branch = "DETACHED"


    # -------------------------------------------------
    # CHANGES
    # -------------------------------------------------

    status = git_command(
        project,

        [
            "status",

            "--porcelain"
        ]
    )


    if status:

        changed_files = [

            line

            for line
            in status.splitlines()

            if line.strip()

        ]

        changes = len(
            changed_files
        )

    else:

        changes = 0


    # -------------------------------------------------
    # CLEAN / CHANGES
    # -------------------------------------------------

    if changes == 0:

        git_state = "CLEAN"

    else:

        git_state = "CHANGES"


    # -------------------------------------------------
    # COMMITS
    # -------------------------------------------------

    commits = git_command(
        project,

        [
            "rev-list",

            "--count",

            "HEAD"
        ]
    )


    if not commits:

        commits = "0"


    # -------------------------------------------------
    # RETURN
    # -------------------------------------------------

    return {

        "git": git_state,

        "branch": branch,

        "changes": str(
            changes
        ),

        "commits": str(
            commits
        )
    }


# =====================================================
# SEND COMMAND TO CONTROLLER
# =====================================================

def send_to_controller(
    command
):

    print()
    print(
        "Sending:",
        command
    )


    try:

        result = subprocess.run(

            [
                "python3",

                CONTROLLER,

                command
            ],

            capture_output=True,

            text=True,

            timeout=20
        )


        if result.stdout:

            print(
                result.stdout
            )


        if result.stderr:

            print(
                result.stderr
            )


        if result.returncode != 0:

            print(
                "Controller exited with code:",
                result.returncode
            )


    except Exception as error:

        print(
            "Controller error:",
            error
        )


# =====================================================
# SEND PROJECT INFORMATION
# =====================================================

def send_project(
    project_path,
    project_name
):

    global last_command


    # -------------------------------------------------
    # GET GIT
    # -------------------------------------------------

    git = get_git_status(
        project_path
    )


    # -------------------------------------------------
    # CREATE DEV COMMAND
    # -------------------------------------------------

    command = "|".join(

        [

            "DEV",

            project_name,

            git["git"],

            git["branch"],

            git["changes"],

            git["commits"]

        ]

    )


    # -------------------------------------------------
    # DON'T SEND DUPLICATE
    # -------------------------------------------------

    if command == last_command:

        return


    last_command = command


    # -------------------------------------------------
    # DISPLAY TERMINAL INFORMATION
    # -------------------------------------------------

    print()
    print(
        "================================"
    )

    print(
        "      ARC STATION DEVELOPER"
    )

    print(
        "================================"
    )

    print(
        "Project :",
        project_name
    )

    print(
        "Path    :",
        project_path
    )

    print(
        "Git     :",
        git["git"]
    )

    print(
        "Branch  :",
        git["branch"]
    )

    print(
        "Changes :",
        git["changes"]
    )

    print(
        "Commits :",
        git["commits"]
    )

    print(
        "Command :",
        command
    )

    print(
        "================================"
    )


    # -------------------------------------------------
    # SEND BLE COMMAND
    # -------------------------------------------------

    send_to_controller(
        command
    )


# =====================================================
# MAIN TRACKER
# =====================================================

def main():

    global last_project
    global last_command


    print()

    print(
        "================================"
    )

    print(
        "        ARC STATION"
    )

    print(
        "   AUTOMATIC PROJECT TRACKER"
    )

    print(
        "================================"
    )

    print()

    print(
        "Watching VS Code..."
    )

    print()


    # =================================================
    # CONTINUOUS TRACKING
    # =================================================

    while True:

        # ---------------------------------------------
        # GET FRONT VS CODE WINDOW
        # ---------------------------------------------

        window_title = (
            get_vscode_window_title()
        )


        if not window_title:

            time.sleep(
                CHECK_INTERVAL
            )

            continue


        # ---------------------------------------------
        # EXTRACT PROJECT NAME
        # ---------------------------------------------

        project_name = (
            clean_project_name(
                window_title
            )
        )


        if not project_name:

            time.sleep(
                CHECK_INTERVAL
            )

            continue


        # ---------------------------------------------
        # FIND PROJECT DIRECTORY
        # ---------------------------------------------

        project_path = (
            find_project_folder(
                project_name
            )
        )


        # ---------------------------------------------
        # PROJECT NOT FOUND
        # ---------------------------------------------

        if not project_path:

            print(
                "VS Code:",
                project_name,
                "→ folder not found"
            )

            time.sleep(
                CHECK_INTERVAL
            )

            continue


        # ---------------------------------------------
        # PROJECT CHANGED
        # ---------------------------------------------

        if project_path != last_project:

            print()
            print(
                "PROJECT DETECTED"
            )

            print(
                "Name:",
                project_name
            )

            print(
                "Path:",
                project_path
            )

            print()


            last_project = project_path


            # Force new project update

            last_command = ""


        # ---------------------------------------------
        # SEND PROJECT DATA
        # ---------------------------------------------

        send_project(

            project_path,

            project_name
        )


        # ---------------------------------------------
        # WAIT
        # ---------------------------------------------

        time.sleep(
            CHECK_INTERVAL
        )


# =====================================================
# START PROGRAM
# =====================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()

        print(
            "ARC STATION TRACKER STOPPED"
        )