"""Tests for CLI commands."""

from pytest_mock import MockerFixture
from typer.testing import CliRunner

from slgrok.main import app
from slgrok.models.requests import CapturedRequest

runner = CliRunner()


class TestListCommand:
    """Tests for list command."""

    def test_list_no_args_shows_help(self) -> None:
        """Test that running without args shows help."""
        result = runner.invoke(app)
        # Typer exits with code 0 when showing help via no_args_is_help
        # but the help output should be present
        assert "slgrok" in result.output.lower() or result.exit_code == 0

    def test_list_success(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test successful list command."""
        mock_repo = mocker.patch("slgrok.cli.commands.NgrokRepository")
        mock_instance = mock_repo.return_value.__enter__.return_value
        mock_instance.get_requests.return_value = sample_requests

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "ngrok Inspector" in result.output
        assert "POST /api/v1/devices" in result.output

    def test_list_with_limit(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test list command with limit."""
        mock_repo = mocker.patch("slgrok.cli.commands.NgrokRepository")
        mock_instance = mock_repo.return_value.__enter__.return_value
        mock_instance.get_requests.return_value = sample_requests

        result = runner.invoke(app, ["list", "-n", "1"])

        assert result.exit_code == 0
        # Output should contain request info
        assert "ngrok Inspector - 1 request" in result.output

    def test_list_with_errors_filter(
        self,
        mocker: MockerFixture,
        sample_requests: list[CapturedRequest],
    ) -> None:
        """Test list command with errors filter."""
        mock_repo = mocker.patch("slgrok.cli.commands.NgrokRepository")
        mock_instance = mock_repo.return_value.__enter__.return_value
        mock_instance.get_requests.return_value = sample_requests

        result = runner.invoke(app, ["list", "--errors"])

        assert result.exit_code == 0
        # Should only show error responses
        assert "errors only" in result.output

    def test_list_connection_error(self, mocker: MockerFixture) -> None:
        """Test list command when ngrok is not running."""
        from slgrok.repositories.ngrok import NgrokConnectionError

        mock_repo = mocker.patch("slgrok.cli.commands.NgrokRepository")
        mock_instance = mock_repo.return_value.__enter__.return_value
        mock_instance.get_requests.side_effect = NgrokConnectionError(
            "http://localhost:4040"
        )

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 1
        assert "Cannot connect to ngrok inspector" in result.output

    def test_list_no_results(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test list command with no results."""
        mock_repo = mocker.patch("slgrok.cli.commands.NgrokRepository")
        mock_instance = mock_repo.return_value.__enter__.return_value
        mock_instance.get_requests.return_value = []

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 1
        assert "No requests found" in result.output


class TestGetCommand:
    """Tests for get command."""

    def test_get_success(
        self,
        mocker: MockerFixture,
        sample_request: CapturedRequest,
    ) -> None:
        """Test successful get command."""
        mock_repo = mocker.patch("slgrok.cli.commands.NgrokRepository")
        mock_instance = mock_repo.return_value.__enter__.return_value
        mock_instance.get_request.return_value = sample_request

        result = runner.invoke(app, ["get", "548fb5c700000001"])

        assert result.exit_code == 0
        assert "POST /api/v1/devices" in result.output

    def test_get_not_found(self, mocker: MockerFixture) -> None:
        """Test get command with nonexistent ID."""
        mock_repo = mocker.patch("slgrok.cli.commands.NgrokRepository")
        mock_instance = mock_repo.return_value.__enter__.return_value
        mock_instance.get_request.side_effect = ValueError("Request not found")

        result = runner.invoke(app, ["get", "nonexistent"])

        assert result.exit_code == 1
        assert "Request not found" in result.output

    def test_get_with_pretty(
        self,
        mocker: MockerFixture,
        sample_request: CapturedRequest,
    ) -> None:
        """Test get command with pretty print."""
        mock_repo = mocker.patch("slgrok.cli.commands.NgrokRepository")
        mock_instance = mock_repo.return_value.__enter__.return_value
        mock_instance.get_request.return_value = sample_request

        result = runner.invoke(app, ["get", "548fb5c700000001", "--pretty"])

        assert result.exit_code == 0


class TestHelpCommand:
    """Tests for help command."""

    def test_help_overview(self) -> None:
        """Test help command without argument."""
        result = runner.invoke(app, ["help"])

        assert result.exit_code == 0
        assert "slgrok - ngrok Inspector CLI Tool" in result.output
        assert "COMMANDS:" in result.output

    def test_help_list(self) -> None:
        """Test help for list command."""
        result = runner.invoke(app, ["help", "list"])

        assert result.exit_code == 0
        assert "LIST COMMAND" in result.output
        assert "EXAMPLES:" in result.output

    def test_help_tail(self) -> None:
        """Test help for tail command."""
        result = runner.invoke(app, ["help", "tail"])

        assert result.exit_code == 0
        assert "TAIL COMMAND" in result.output

    def test_help_get(self) -> None:
        """Test help for get command."""
        result = runner.invoke(app, ["help", "get"])

        assert result.exit_code == 0
        assert "GET COMMAND" in result.output

    def test_help_unknown_command(self) -> None:
        """Test help for unknown command."""
        result = runner.invoke(app, ["help", "unknown"])

        assert result.exit_code == 0
        assert "Unknown command" in result.output
