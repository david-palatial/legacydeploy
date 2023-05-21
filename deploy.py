import sys
import subprocess
import os
import time
import queue
import threading

def reset(branch, dir_name, container_tag):
  print(f"(1/4) Delete {branch}")
  subprocess.run(f"sps-client application delete --name {branch}")
  sys.stdout.write("(2/4) Creating application")
  print_dots(25)
  subprocess.run(f"sps-client application create --name {branch}")
  sys.stdout.write("(3/4) Creating version...")
  subprocess.run(f"sps-client version create --application {branch} --name {dir_name} --buildOptions.input.containerTag {container_tag} --buildOptions.credentials.registry \"https://index.docker.io/v1/\"")
  sys.stdout.write("(4/4) Setting active version...\n")
  subprocess.run(f"sps-client application update --name {branch} --activeVersion {dir_name}")
  sys.stdout.write("Finishing up")
  print_dots(18)
  print(f"\n{branch} reset: https://{branch}.palatialxr.com")

def show_help():
  print("usage: deploy <dir> [-b or --branch] <branch> [options...]\n\
-A, --app-only     Only deploy the client\n\
-b, --branch       The application branch to deploy to (dev, demo, prophet, etc.)\n\
-h, --help         Get help for commands\n\
-r, --reset-app    Deletes and recreates the application\n\
-S, --server-only  Only deploy the server\n")
  print("Example: deploy 22-11-23_build-A-CD --branch dev")

def print_periodic(duration):
    end_time = time.time() + duration
    while time.time() < end_time:
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(1)

def print_dots(duration):
    q = queue.Queue()

    def print_dots_thread():
        end_time = time.time() + duration
        while time.time() < end_time:
            q.put(". ")
            time.sleep(1)
        q.put(None)  # Signal end of dots

    thread = threading.Thread(target=print_dots_thread)
    thread.start()

    while True:
        item = q.get()
        if item is None:
            break
        print(item, end="")
        sys.stdout.flush()

branch=None
build=None
app_only = False
server_only = False
reset_app = False

options = ["-h","--help","-A","-b","--branch","-h","--help","-r","--reset-app","-S","--server-only"]

if len(sys.argv) < 2:
  show_help()
  sys.exit(1)

dir_name = os.path.abspath(sys.argv[1])

for i in range(1, len(sys.argv)):
  opt = sys.argv[i]
  if opt[0] == '-' and opt not in options:
    print(f"Invalid option {opt}")
    show_help()
    sys.exit(1)
  if opt == "--help" or opt == "-h":
    show_help()
    sys.exit(0)
  if opt == "--branch" or opt == "-b":
    if i+1 >= len(sys.argv):
      print("error: --branch provided without an argument")
      sys.exit(1)
    branch = sys.argv[i+1]
  if opt == "-A" or opt == "--app-only":
    app_only = True
  if opt == "-S" or opt == "--server-only":
    server_only = True
  if opt == "-r" or opt == "--reset-app":
    reset_app = True

if not os.path.exists(dir_name):
  print(f"Directory {dir_name} does not exist.")
  sys.exit(1)

if app_only and not os.path.exists(os.path.join(dir_name, "LinuxClient")):
  print("error: file LinuxClient does not exist".format(dir_name))
  sys.exit(1)

if server_only and not os.path.exists(os.path.join(dir_name, "LinuxServer")):
  print("error: file LinuxServer does not exist".format(dir_name))
  sys.exit(1)

if branch == None:
  print("error: -b or --branch is required (one of dev, prophet, demo, etc..)")
  print("Example: deploy 22-11-23_build-A-CD --branch dev")
  sys.exit(1)

container_tag = f"index.docker.io/dgodfrey206/palatialsps:{branch}"

if reset_app == True:
  reset(branch, os.path.basename(dir_name), container_tag)
  sys.exit(0)

os.chdir(dir_name)

if not server_only:
  os.chdir("LinuxClient")
  subprocess.run(f"image-builder create --package . --tag {container_tag}")
  reset(branch, dir_name, container_tag)
  if app_only:
    sys.stdout.write("Finishing up")
    print_periodic(15)
  os.chdir("..")

if not app_only:
  print("Uploading server...")
  subprocess.run(f"ssh david@prophet.palatialxr.com \"sudo systemctl stop server_{branch}.service\"")
  subprocess.check_output("scp -r LinuxServer david@prophet.palatialxr.com:~/servers/" + branch)
  subprocess.run(f"ssh david@prophet.palatialxr.com \"sudo systemctl start server_{branch}.service\"")

print("Successfully deployed")