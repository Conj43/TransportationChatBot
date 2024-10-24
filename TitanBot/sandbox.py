# code used from https://github.com/typper-io/ai-code-sandbox
# has bene modified to fit our needs


import docker, shlex, uuid, textwrap, os, tarfile, io, time, csv, re
from io import BytesIO
from bs4 import BeautifulSoup


class AICodeSandbox:
    """
    A sandbox environment for executing Python code safely.

    This class creates a Docker container with a Python environment,
    optionally installs additional packages, and provides methods to
    execute code, read and write files within the sandbox.

    Attributes:
        client (docker.DockerClient): Docker client for managing containers and images.
        container (docker.models.containers.Container): The Docker container used as a sandbox.
        temp_image (docker.models.images.Image): Temporary Docker image created for the sandbox.
    """

    def __init__(self, custom_image=None, packages=None, network_mode="none", mem_limit="400m", cpu_period=100000, cpu_quota=50000):
        """
        Initialize the PythonSandbox.

        Args:
            custom_image (str, optional): Name of a custom Docker image to use. Defaults to None.
            packages (list, optional): List of Python packages to install in the sandbox. Defaults to None.
            network_mode (str, optional): Network mode to use for the sandbox. Defaults to "none".
            mem_limit (str, optional): Memory limit for the sandbox. Defaults to "400m".
            cpu_period (int, optional): CPU period for the sandbox. Defaults to 100000.
            cpu_quota (int, optional): CPU quota for the sandbox. Defaults to 50000.
        """
        self.client = docker.from_env()
        self.container = None
        self.temp_image = None
        self._setup_sandbox(custom_image, packages, network_mode, mem_limit, cpu_period, cpu_quota)

    def _setup_sandbox(self, custom_image, packages, network_mode, mem_limit, cpu_period, cpu_quota):
        """Set up the sandbox environment."""
        image_name = custom_image or "python:3.9-slim"
        
        if packages:
            dockerfile = f"FROM {image_name}\nRUN pip install {' '.join(packages)}"
            dockerfile_obj = BytesIO(dockerfile.encode('utf-8'))
            self.temp_image = self.client.images.build(fileobj=dockerfile_obj, rm=True)[0]
            image_name = self.temp_image.id

        self.container = self.client.containers.run(
            image_name,
            name=f"python_sandbox_{uuid.uuid4().hex[:8]}",
            command="tail -f /dev/null",
            detach=True,
            network_mode=network_mode,
            mem_limit=mem_limit,
            cpu_period=cpu_period,
            cpu_quota=cpu_quota
        )

    # use this to copy temp db into sandbox
    def write_file(self, filename, content):
        """
        Write content to a file in the sandbox, creating directories if they don't exist.

        Args:
            filename (str): Name of the file to create or overwrite.
            content (bytes): Content to write to the file in binary format.

        Raises:
            Exception: If writing to the file fails.
        """
        
        if not self.is_allowed_file(filename):
            raise Exception(f"File name '{filename}' is not allowed.")
        

        if isinstance(content, str): # if input is string, convert to bytes
            content = content.encode('utf-8')

        directory = os.path.dirname(filename)
        if directory and directory != '/':
            mkdir_command = f'mkdir -p {shlex.quote(directory)}'
            mkdir_result = self.container.exec_run(["sh", "-c", mkdir_command])
            if mkdir_result.exit_code != 0:
                raise Exception(f"Failed to create directory: {mkdir_result.output.decode('utf-8')}")

        # create a tar archive containing the file
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(content)
            tar.addfile(tarinfo, io.BytesIO(content))

        tar_stream.seek(0)

        try:
            # upload the tar archive to the container
            self.container.put_archive(os.path.dirname(filename), tar_stream)
        except Exception as e:
            raise Exception(f"Failed to write file: {str(e)}")

        # verify that the file was created
        check_command = f'test -f {shlex.quote(filename)}'
        check_result = self.container.exec_run(["sh", "-c", check_command])
        if check_result.exit_code != 0:
            raise Exception(f"Failed to write file: {filename}")

    # use this to copy files from sandbox to UI
    def read_file(self, filename):
        """
        Read content from a file in the sandbox.

        Args:
            filename (str): Name of the file to read.

        Returns:
            str or bytes: Content of the file. Decodes to str if text, otherwise returns bytes.

        Raises:
            Exception: If reading the file fails.
        """

        if not self.is_allowed_file(filename):
            raise Exception(f"File name '{filename}' is not allowed.")

        try:
            # read file content as a tar archive
            bits, _ = self.container.get_archive(filename)
            
            # extract file content from tar archive
            tar_stream = io.BytesIO(b''.join(bits))
            with tarfile.open(fileobj=tar_stream, mode='r') as tar:
                # list all members to find exact name
                members = tar.getmembers()
                filenames_in_tar = [member.name for member in members]


                
                # check if the file exists in the tar archive
                if filename not in filenames_in_tar:
                    raise Exception(f"File '{filename}' not found in the tar archive.")
                
                # extract the specific file
                file = tar.extractfile(filename)
                if file is not None:
                    file_content = file.read()

                    # Attempt to decode as UTF-8 text
                    try:
                        decoded_content = file_content.decode('utf-8')
                        # check for html files
                        if filename.lower().endswith('.html'):
                            soup = BeautifulSoup(decoded_content, 'html.parser')
                            return soup  
                        # check for csv file
                        if filename.lower().endswith('.csv'):
                            try:
                                # parse CSV content
                                csv_reader = csv.reader(io.StringIO(decoded_content))
                                return list(csv_reader)
                            except Exception as e:
                                raise Exception(f"Failed to parse CSV file: {str(e)}")

                        return decoded_content

                    except UnicodeDecodeError:
                        # return as binary data if decoding fails
                        return file_content
                else:
                    raise Exception(f"Failed to extract file from archive: {filename}")

        except Exception as e:
            raise Exception(f"Failed to read file: {str(e)}")






    # runs code passed as a string
    def run_code(self, code, env_vars=None):
        """
        Execute Python code in the sandbox.

        Args:
            code (str): Python code to execute.
            env_vars (dict, optional): Environment variables to set for the execution. Defaults to None.

        Returns:
            str: Output of the executed code or error message.
        """



        if self.contains_harmful_code(code):
            raise Exception("File content contains harmful code.")


        if env_vars is None:
            env_vars = {}
        
        code = textwrap.dedent(code)

        env_str = " ".join(f"{k}={shlex.quote(v)}" for k, v in env_vars.items())
        escaped_code = code.replace("'", "'\"'\"'")
        exec_command = f"env {env_str} python -c '{escaped_code}'"
        
        exec_result = self.container.exec_run(
            ["sh", "-c", exec_command],
            demux=True
        )
        
        if exec_result.exit_code != 0:
            return f"Error (exit code {exec_result.exit_code}): {exec_result.output[1].decode('utf-8')}"
        
        stdout, stderr = exec_result.output
        if stdout is not None:
            return stdout.decode('utf-8') # check for standard output 
        elif stderr is not None:
            return f"Error: {stderr.decode('utf-8')}" # chek for errors
        else:
            return "No output" # return no output if no standard output or error

    # cleans up dandbox
    def close(self):
        """Remove all resources created by this sandbox."""
        if self.container:
            try:
                print("Stopping container...")
                self.container.stop(timeout=10)  # stop container with a timeout
                print("Removing container...")
                self.container.remove(force=True)  # force remove container
                print("Container stopped and removed successfully.")
            except docker.errors.APIError as e:
                print(f"API error while stopping/removing container: {str(e)}")
            except docker.errors.NotFound as e:
                print(f"Container not found during cleanup: {str(e)}")
            except Exception as e:
                print(f"Unexpected error during cleanup: {str(e)}")
            finally:
                self.container = None

        time.sleep(1)  # make sure container has time to be removed

        if self.temp_image:
            try:
                for _ in range(3):
                    try:
                        print(f"Removing image {self.temp_image.id}...")
                        self.client.images.remove(self.temp_image.id, force=True)
                        print("Image removed successfully.")
                        break
                    except docker.errors.APIError as e:
                        print(f"Attempt to remove image failed: {str(e)}")
                        time.sleep(2)
                else:
                    print("Failed to remove temporary image after multiple attempts")
            except Exception as e:
                print(f"Error removing temporary image: {str(e)}")
            finally:
                self.temp_image = None

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.close()

    
    def is_allowed_file(self, filename):
        # define extensions to be allowed
        allowed_extensions = ['.txt', '.csv', '.html', '.db', '.png']

        # file name we use for all dbs that user inputs
        allowed_files = ['/your_db.db']

        # allow '/your_db.db'
        if filename in allowed_files:
            return True


        disallowed_pattern = r'[^a-zA-Z0-9_.-]'  # allow letters, numbers, underscores, periods, and dashes

        # check file extension extension
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            return False
        
        # check file name
        if re.search(disallowed_pattern, filename):
            return False

        return True # return true if there were no illegal extensions or names
    

    def contains_harmful_code(self, content):
        # check for harmful patterms such as:
        # subprocess, eval, exec, os.system, os.remove, open, shutil, os and sys are all not allowed to appear in code to be executed
        # also cannot use __import__, globals or locals
        harmful_patterns = [
            r'\b(import os|import sys|subprocess|eval|exec|os.system|os.remove|open\([^)]*|shutil)\b',
            r'\b(__import__|globals|locals)\b'
        ]

        # check code for harmful patterns
        for pattern in harmful_patterns:
            if re.search(pattern, content):
                return True

        return False
    





