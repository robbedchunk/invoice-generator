# Contributing

Thanks for your interest in contributing!

## How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`python -m unittest discover -s tests -p "test_*.py"`)
5. Test locally by running the server and sending a sample invoice payload
6. Commit your changes (`git commit -m "Add my feature"`)
7. Push to the branch (`git push origin feature/my-feature`)
8. Open a Pull Request

## Reporting Issues

Open an issue on GitHub with:
- A description of the problem
- The JSON payload that triggered it (if applicable)
- Expected vs actual behavior

## Code Style

- Follow existing module boundaries and naming conventions
- Keep functions focused and composable
- Add type hints for new public functions/classes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
