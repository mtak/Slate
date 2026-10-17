# Contributing to Slate

Thanks for your interest in Slate. Contributions that improve the display,
server, firmware, documentation, or setup experience are welcome.

## Before you start

- For a substantial change, open an issue first to discuss the approach.
- Keep changes focused and follow the existing structure and conventions.
- Keep integrations on the server and independent of one another.
- Preserve the 800×480 monochrome frame contract and keep the firmware focused
  on fetching and displaying frames.
- Use fictional data and placeholders in examples. Never commit credentials,
  device tokens, private calendar URLs, household information, private network
  details, or machine-specific configuration.

## Making a change

1. Create a branch for your work.
2. Make the change and update relevant documentation or examples.
3. Run the checks relevant to the files you changed:
   - Firmware: from `firmware/`, run `make test` and `make build`.
   - Server: follow the sample render workflow in [the server guide](server/README.md).
   - Hardware or display changes: document any checks that require the physical
     device and report whether you could perform them.
4. Review the full diff for correctness, accidental secrets, and private data.
   See the [repository hygiene checklist](docs/repository-hygiene.md).
5. Open a pull request describing the problem, the change, and the checks you
   ran. Include screenshots for visual changes when useful.

If a required check cannot be run, say why and describe any other validation
you performed. Do not include real deployment settings or private household
content in issues or pull requests.

## License

By contributing, you agree that your contributions are provided under the
project's [GNU General Public License version 3](LICENSE).
