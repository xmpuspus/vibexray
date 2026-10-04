# Security policy

## Report a vulnerability

Open a private security advisory on the [GitHub repository](https://github.com/xmpuspus/vibexray/security/advisories/new). Do not open a public issue for a vulnerability.

Include the version, the command you ran, and the steps to repeat the problem. You get a reply within 7 days.

## Supported versions

Only the latest release gets fixes.

## What the tool does with your code

- The scan reads files in the folder that you name. It sends nothing over the network.
- The scan runs no code from the scanned folder. An app run happens only when you do not pass `--no-run`.
- An app run installs with `--ignore-scripts` and a clean environment.
- The report hides the secret values that it recognizes, such as API keys and passwords. It shows the file and the line.
