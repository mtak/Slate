# Server

The server gathers household data through independent providers, renders an
800×480 1-bit frame using an editable layout, and serves the latest frame to the
ESP32. It also provides a browser preview for layout development.

The project is being bootstrapped. See GitHub issues
[#5](https://github.com/mtak/Slate/issues/5),
[#6](https://github.com/mtak/Slate/issues/6),
[#7](https://github.com/mtak/Slate/issues/7), and
[#8](https://github.com/mtak/Slate/issues/8) for the frame contract,
renderer/layout, Compose service, and HTTPS/authentication. Python and Pillow
are the current direction; issue #6 will settle implementation details.

This is intended to be a public repository; follow the [public repository
hygiene notes](../docs/architecture.md#public-repository-hygiene). Secrets
belong in deployment configuration outside source control. Providers must
remain server-side and return data through a small common interface.
