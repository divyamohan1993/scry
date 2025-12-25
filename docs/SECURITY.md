# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of this project seriously. If you have discovered a security vulnerability, we appreciate your help in disclosing it to us in a responsible manner.

To report a vulnerability, please email [security@dmj.one](mailto:security@dmj.one) (or the repository owner).

### When reporting a vulnerability:

1.  **Do not create a public GitHub issue.** This allows us to assess the risk and fix the vulnerability before it is exploited.
2.  Provide a detailed description of the vulnerability, including steps to reproduce it.
3.  Are there any known exploits?

We will acknowledge your report within 48 hours and provide an estimated timeline for a fix.

## Security Practices

We enforce the following security practices:

*   **Machine-Bound Encryption**: API keys are encrypted using hardware identifiers.
*   **Ephemeral Licensing**: Optional strict licensing system invalidates sessions on closure.
*   **No Plaintext Secrets**: Secrets are never stored in plaintext after initialization.
*   **Regular Audits**: We regularly scan dependencies for known vulnerabilities.
