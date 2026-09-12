## Guidance for Contributors

We would sincerely appreciate your contributions to the [FastA2A](https://ai.pydantic.dev/a2a/) project.

### Areas of Contribution

You can contribute to the project in the following areas:
- project documentation
- python code updates (adding functionality, fixing bugs, adding code documentation etc.)
- writing new unit tests, fixing existing unit tests
- reporting issues
- making suggestions for feature requests and improvements
- starting and contributing to discussions
- reviewing pull requests
- responding to issues and discussions
- creating examples and tutorials for the [FastA2A](https://ai.pydantic.dev/a2a/) project.

Before reporting new issues, take a look at [existing issues](https://github.com/pydantic/fasta2a/issues) to ensure that you are not creating duplicates.

### Pre-Commit Checks before Sending in your Pull Requests

Clone a fork of the [FastA2A repo](https://github.com/pydantic/fasta2a/fork) and cd into that directory

```bash

git clone git@github.com:<yourUsername>/fasta2a.git

cd fasta2a 

```

Install uv (version 0.4.30 or later)

### Running Lints and Tests etc

Run the following commands before checking in your changes to git. 

Your PR may not be accepted if it fails these checks.

It is usually a good idea to keep the branch in your fork up-to-date with the upstream branch if you are planning 
to work on your changes over an extended period of time.

```bash

# Run linters
uv run scripts/check

# Run unit tests
uv run scripts/test

```

### Additional Questions

If you have additional questions you can check out the #pydantic-ai channel in the Pydantic Slack to ask questions, get help, and chat about FastA2A.

